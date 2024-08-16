#!/usr/bin/env python3

import argparse
import os
import re
import sys
import logging
from datetime import datetime
import random
import string
import traceback
import zipfile
import tarfile
import gzip
import shutil
import tempfile
import getpass


# 设置日志记录器
def setup_logger(log_file=None):
    logger = logging.getLogger('bren')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# 解析命令行参数
def parse_arguments():
    epilog = '''
Examples:
  # Rename all .txt files in the current directory, appending "_old" to the filename
  bren -m suffix:.txt --append "_old"

  # Recursively rename all files starting with "IMG_" in D:\\Photos, replacing "IMG_" with "Photo_"
  bren -p "D:\\Photos" -R -m prefix:IMG_ --replace IMG_ Photo_

  # Preview renaming all .jpg files to add the current date as a prefix
  bren -p "C:\\Users\\YourName\\Pictures" -m suffix:.jpg --prepend "${date}_" -v

  # Rename files containing "draft" to remove "draft" and append "final"
  bren -m contain:draft --delete "draft" --append "_final"

  # Use regex to rename files, adding a number sequence
  bren -m "regex:^[a-z]+_\\d{3}\\.txt$" --append "_####"

  # Rename files with a number sequence, skipping every other number
  bren -m suffix:.jpg --append "_####" --num-start 1 --num-step 2

  # Rename files without creating a rollback log
  bren -m suffix:.txt --append "_new" --no-log

  # Rollback a previous rename operation
  bren --rollback "C:\\path\\to\\logfile_ren_20240815_221015333.log"
'''

    parser = argparse.ArgumentParser(
        description="Batch rename files and directories",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-p', '--path', help="Specify the path to process")
    parser.add_argument('-g', '--archive', help="Specify an archive file (zip, gz, tar) to process")
    parser.add_argument('-R', '--recursive', action='store_true', help="Recursive operation")
    parser.add_argument('-f', '--file-only', action='store_true', help="Match files only")
    parser.add_argument('-d', '--dir-only', action='store_true', help="Match directories only")
    parser.add_argument('-x', '--exclude', action='append', help="Exclude pattern")
    parser.add_argument('-v', '--preview', action='store_true', help="Preview mode")
    parser.add_argument('-l', '--log', help="Log file path")
    parser.add_argument('--dry-run', action='store_true', help="Simulate renaming without actual changes")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-m', '--match', help="Match pattern (type:pattern)")
    group.add_argument('--rollback', help="Roll back operations using the specified log file")
    
    # Actions
    parser.add_argument('--delete', help="Delete matching characters")
    parser.add_argument('--replace', nargs=2, metavar=('OLD', 'NEW'), help="Replace characters")
    parser.add_argument('--append', help="Append characters")
    parser.add_argument('--prepend', help="Prepend characters")
    parser.add_argument('--attr', help="Modify attributes")
    
    # Special parameters
    parser.add_argument('--num-start', type=int, default=1, help="Starting number for sequence")
    parser.add_argument('--num-step', type=int, default=1, help="Step between numbers in sequence")
    parser.add_argument('--num-format', default='#', help="Number format")
    parser.add_argument('--date-format', default='ms', help="Date format or 'ms' for milliseconds")
    parser.add_argument('--random', type=int, default=8, help="Random string length (default: 8)")
    parser.add_argument('--random-lowercase', action='store_true', help="Use only lowercase letters for random string")
    parser.add_argument('--random-uppercase', action='store_true', help="Use only uppercase letters for random string")
    parser.add_argument('--sort', choices=['name', 'mtime', 'ctime'], help="Sort files by name, modification time, or creation time")

    parser.add_argument('--no-log', action='store_true', help="Don't create a rollback log file")

    parser.add_argument('paths', nargs='*', default=[], help="Paths to files or directories. If not provided, uses current directory or path specified by -p.")
    args = parser.parse_args()

    # 处理路径参数
    if args.path:
        args.paths = [args.path]
    elif not args.paths and sys.stdin.isatty():
        args.paths = ['.']
    elif not args.paths and not sys.stdin.isatty():
        args.paths = [line.strip() for line in sys.stdin]

    return args


# 验证命令行参数
def validate_args(args):
    if args.file_only and args.dir_only:
        raise ValueError("Cannot specify both --file-only and --dir-only")
    
    if not any([args.delete, args.replace, args.append, args.prepend, args.attr]):
        raise ValueError("At least one action (delete, replace, append, prepend, attr) must be specified")
    
    if args.random and args.random < 1:
        raise ValueError("Random string length must be positive")
    
    if ':' not in args.match:
        raise ValueError("Match pattern must be in the format 'type:pattern'")
    
    match_type, _ = args.match.split(':', 1)
    if match_type not in ['prefix', 'suffix', 'contain', 'regex']:
        raise ValueError(f"Invalid match type: {match_type}")
    
    if args.rollback and (args.match or args.delete or args.replace or args.append or args.prepend):
        raise ValueError("Rollback cannot be combined with other operations")
    
    if not args.rollback and not args.match:
        raise ValueError("Match pattern is required for rename operations")
    
    if args.archive:
        if not args.archive.lower().endswith(('.zip', '.gz', '.tar')):
            raise ValueError("Unsupported archive format. Use .zip, .gz, or .tar")
        if not args.no_log:
            args.no_log = True
            print("Warning: Log and rollback features are disabled when processing archives.")
        args.paths = [args.archive]  # 将 archive 路径添加到 paths 中
    elif not args.paths:
        args.paths = ['.']  # 如果没有指定路径和归档文件，使用当前目录
    
    for path in args.paths:
        if not os.path.exists(path):
            raise ValueError(f"Specified path does not exist: {path}")


def process_archive(archive_path, match_pattern, operations, args, logger):
    temp_dir = tempfile.mkdtemp()
    archive_dir = os.path.dirname(archive_path)
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    try:
        # Extract archive
        if archive_path.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        elif archive_path.lower().endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar_ref:
                tar_ref.extractall(temp_dir)
        elif archive_path.lower().endswith('.gz'):
            with gzip.open(archive_path, 'rb') as gz_ref:
                with open(os.path.join(temp_dir, os.path.basename(archive_path)[:-3]), 'wb') as out_f:
                    shutil.copyfileobj(gz_ref, out_f)

        # Process files
        batch_rename(temp_dir, match_pattern, operations, args, logger, archive_name)

        # Repack archive
        if archive_path.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'w') as zip_ref:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        zip_ref.write(os.path.join(root, file), 
                                      os.path.relpath(os.path.join(root, file), temp_dir))
        elif archive_path.lower().endswith('.tar'):
            with tarfile.open(archive_path, 'w') as tar_ref:
                tar_ref.add(temp_dir, arcname='')
        elif archive_path.lower().endswith('.gz'):
            with open(os.path.join(temp_dir, os.path.basename(archive_path)[:-3]), 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

    finally:
        shutil.rmtree(temp_dir)


def batch_rename(path, match_pattern, rename_operations, args, logger, archive_name=None):
    match_type, pattern = match_pattern.split(':', 1)
    log_entries = []
    log_path = None
    
    if not args.no_log and not args.preview and not args.dry_run:
        # 创建日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
        log_filename = f"{os.path.basename(path)}_ren_{timestamp}.log"
        log_path = os.path.join(path, log_filename)
    
    sequence_index = 1
    renamed_files = []

    for root, dirs, files in os.walk(path):
        if not args.recursive and root != path:
            break
        
        items = get_matching_files(root, match_type, pattern, args)
        
        for item in items:
            old_name = os.path.join(root, item)
            new_name = item
            temp_vars = []
            
            for op, value in rename_operations:
                if op == 'delete':
                    new_name, deleted = delete_pattern(new_name, value)
                    temp_vars.append(deleted)
                elif op == 'replace':
                    new_name, replaced = replace_pattern(new_name, value[0], value[1])
                    temp_vars.append(replaced)
                elif op == 'append':
                    new_name = append_pattern(new_name, value, args, sequence_index, temp_vars, archive_name or root)
                elif op == 'prepend':
                    new_name = prepend_pattern(new_name, value, args, sequence_index, temp_vars, archive_name or root)
                elif op == 'attr':
                    modify_attributes(old_name, value, args)
            
            new_path = os.path.join(root, new_name)
            renamed_files.append(new_path)

            sequence_index += 1
            
            if args.preview or args.dry_run:
                logger.info(f"Would rename '{old_name}' to '{new_path}'")
            else:
                try:
                    os.rename(old_name, new_path)
                    logger.info(f"Renamed '{old_name}' to '{new_path}'")
                    if not args.no_log:
                        log_entries.append(f"{old_name},{new_path}")
                except OSError as e:
                    logger.error(f"Failed to rename '{old_name}': {str(e)}")
    
    # 写入日志文件
    if log_path and log_entries:
        with open(log_path, 'w') as log_file:
            for entry in log_entries:
                log_file.write(f"{entry}\n")
        logger.info(f"Rename log created: {log_path}")

    return log_path if log_entries else None, renamed_files


# 获取匹配的文件和文件夹
def get_matching_files(path, match_type, pattern, args):
    items = []
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if args.file_only and not os.path.isfile(full_path):
            continue
        if args.dir_only and not os.path.isdir(full_path):
            continue
        if args.exclude and any(exclude_match(item, ex) for ex in args.exclude):
            continue
        if match_file(item, match_type, pattern):
            items.append((item, full_path))
    
    if args.sort == 'name':
        return [f[0] for f in sorted(items)]
    elif args.sort == 'mtime':
        return [f[0] for f in sorted(items, key=lambda x: os.path.getmtime(x[1]))]
    elif args.sort == 'ctime':
        return [f[0] for f in sorted(items, key=lambda x: os.path.getctime(x[1]))]
    else:
        return [f[0] for f in items]


# 文件匹配函数
def match_file(filename, match_type, pattern):
    if match_type == 'prefix':
        return filename.startswith(pattern)
    elif match_type == 'suffix':
        return filename.endswith(pattern)
    elif match_type == 'contain':
        return pattern in filename
    elif match_type == 'regex':
        return re.match(pattern, filename) is not None
    return False


# 排除匹配函数
def exclude_match(filename, pattern):
    return match_file(filename, 'contain', pattern)


# 删除模式函数
def delete_pattern(filename, pattern):
    deleted = re.findall(pattern, filename)
    return re.sub(pattern, '', filename), ''.join(deleted)


# 替换模式函数
def replace_pattern(filename, old, new):
    replaced = re.findall(re.escape(old), filename)
    return filename.replace(old, new), ''.join(replaced)


# 追加模式函数
def append_pattern(filename, pattern, args, index, temp_vars, root):
    base, ext = os.path.splitext(filename)
    pattern = process_pattern(pattern, args, index, temp_vars, root)
    return f"{base}{pattern}{ext}"


# 前置模式函数
def prepend_pattern(filename, pattern, args, index, temp_vars, root):
    pattern = process_pattern(pattern, args, index, temp_vars, root)
    return f"{pattern}{filename}"


# 处理模式字符串
def process_pattern(pattern, args, index, temp_vars, root):
    pattern = pattern.replace('$W', os.path.basename(root))
    pattern = pattern.replace('$U', getpass.getuser())
    
    # 处理带有子参数的日期模式
    pattern = re.sub(r'\${date(:([^}]+))?}', lambda m: get_date_string(m.group(2) or args.date_format), pattern)
    
    # 处理带有子参数的随机字符串模式
    pattern = re.sub(r'\${random(:(\d+))?}', lambda m: generate_random_string(int(m.group(2)) if m.group(2) else args.random, get_random_char_set(args)), pattern)
    
    if '#' in pattern:
        actual_number = args.num_start + (index - 1) * args.num_step
        num_str = str(actual_number).zfill(pattern.count('#'))
        pattern = pattern.replace('#' * pattern.count('#'), num_str)
    
    # 处理 ${0}, ${1}, ${2} 等占位符
    for i, var in enumerate(temp_vars):
        pattern = pattern.replace(f'${i}', var)
    
    return pattern


def generate_random_string(length, char_set):
    try:
        length = int(length)
        if length <= 0:
            raise ValueError("Random string length must be a positive integer")
        return ''.join(random.choice(char_set) for _ in range(length))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid random string length: {e}")


def get_random_char_set(args):
    if args.random_lowercase:
        return string.ascii_lowercase
    elif args.random_uppercase:
        return string.ascii_uppercase
    else:
        return string.ascii_letters + string.digits


def get_date_string(date_format):
    if date_format == 'ms':
        return str(int(datetime.now().timestamp() * 1000))
    else:
        return datetime.now().strftime(date_format)


# 获取日期字符串
def get_date_string(date_format):
    if date_format == 'ms':
        return str(int(datetime.now().timestamp() * 1000))
    else:
        return datetime.now().strftime(date_format)


# 生成随机字符串
def generate_random_string(length, char_set):
    return ''.join(random.choice(char_set) for _ in range(length))


# 获取随机字符集
def get_random_char_set(args):
    if args.random_lowercase:
        return string.ascii_lowercase + string.digits
    elif args.random_uppercase:
        return string.ascii_uppercase + string.digits
    else:
        return string.ascii_letters + string.digits


# 修改文件属性
def modify_attributes(filepath, attrs, args):
    if args.preview or args.dry_run:
        return
    
    try:
        current_mode = os.stat(filepath).st_mode
        new_mode = current_mode

        if 'r' in attrs:
            new_mode |= 0o444 if not attrs.startswith('-') else ~0o444
        if 'w' in attrs:
            new_mode |= 0o222 if not attrs.startswith('-') else ~0o222
        if 'x' in attrs:
            new_mode |= 0o111 if not attrs.startswith('-') else ~0o111

        os.chmod(filepath, new_mode)

        if 'h' in attrs:
            if os.name == 'nt':  # Windows
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_HIDDEN)
            else:  # Unix-like
                new_name = os.path.join(os.path.dirname(filepath), f".{os.path.basename(filepath)}")
                os.rename(filepath, new_name)
    except OSError as e:
        raise OSError(f"Failed to modify attributes for '{filepath}': {str(e)}")


# 回退操作
def rollback(log_file, logger):
    if not os.path.exists(log_file):
        logger.error(f"Log file '{log_file}' not found.")
        return

    with open(log_file, 'r') as f:
        for line in f:
            old_name, new_name = line.strip().split(',')
            if os.path.exists(new_name):
                try:
                    os.rename(new_name, old_name)
                    logger.info(f"Rolled back: '{new_name}' to '{old_name}'")
                except OSError as e:
                    logger.error(f"Failed to roll back '{new_name}': {str(e)}")
            else:
                logger.warning(f"File '{new_name}' not found, skipping rollback.")

    # 操作完成后删除日志文件
    try:
        os.remove(log_file)
        logger.info(f"Removed log file: {log_file}")
    except OSError as e:
        logger.error(f"Failed to remove log file '{log_file}': {str(e)}")


# 安全重命名函数
def safe_rename(old_name, new_name, logger):
    try:
        if os.path.exists(new_name):
            raise OSError(f"Destination '{new_name}' already exists")
        os.rename(old_name, new_name)
        logger.info(f"Renamed '{old_name}' to '{new_name}'")
    except OSError as e:
        logger.error(f"Failed to rename '{old_name}': {str(e)}")
        raise


# 检查是否有足够的权限
def check_permissions(path):
    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise PermissionError(f"Insufficient permissions to access '{path}'")


# 主函数
def main():
    args = parse_arguments()
    logger = setup_logger(args.log)
    
    try:
        if args.rollback:
            rollback(args.rollback, logger)
        else:
            validate_args(args)
            
            rename_operations = []
            if args.delete:
                rename_operations.append(('delete', args.delete))
            if args.replace:
                rename_operations.append(('replace', args.replace))
            if args.append:
                rename_operations.append(('append', args.append))
            if args.prepend:
                rename_operations.append(('prepend', args.prepend))
            if args.attr:
                rename_operations.append(('attr', args.attr))
            
            all_renamed_files = []
            log_path = None
            for path in args.paths:
                check_permissions(path)
                logger.info(f"processing path: {path}")
                if args.archive and path == args.archive:
                    process_archive(path, args.match, rename_operations, args, logger)
                else:
                    current_log_path, renamed_files = batch_rename(path, args.match, rename_operations, args, logger)
                    all_renamed_files.extend(renamed_files)
                    if current_log_path:
                        log_path = current_log_path
            
            if log_path:
                logger.info(f"To rollback this operation, use: bren --rollback {log_path}")
            elif not args.no_log and not args.preview and not args.dry_run:
                logger.info("No files were renamed, so no log file was created.")
            
            # 输出重命名的文件路径，使用 null 字符分隔
            if not args.preview and not args.dry_run:
                for file in all_renamed_files:
                    sys.stdout.buffer.write(file.encode('utf-8') + b'\0')
                sys.stdout.buffer.flush()
    
    except ValueError as e:
        logger.error(f"Invalid argument: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        sys.exit(1)
    except PermissionError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
