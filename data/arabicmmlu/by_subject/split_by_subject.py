import pandas as pd
import os
import glob # 用于查找文件

def combine_and_split_by_subject():
    """
    读取多个 'arabicmmlu_*.csv' 文件, 合并它们,
    然后根据 'Subject' 列的值将数据拆分到新的CSV文件中。
    """

    # 1. 找到所有匹配的CSV文件
    # 我们使用用户指定的准确列表
    input_files = [f'arabicmmlu_{i}.csv' for i in range(1, 6)]

    print(f"开始处理 {len(input_files)} 个文件: {', '.join(input_files)}")

    # 2. 读取所有CSV文件并合并到一个DataFrame中
    all_dfs = []
    for f in input_files:
        if not os.path.exists(f):
            print(f"警告：文件 {f} 未找到，将被跳过。")
            continue

        try:
            # 读取CSV文件
            df = pd.read_csv(f)
            all_dfs.append(df)
            print(f"已读取: {f} (包含 {len(df)} 行)")
        except Exception as e:
            print(f"读取文件 {f} 时出错: {e}")

    if not all_dfs:
        print("错误：没有成功读取任何文件。请检查文件名和路径。脚本将退出。")
        return

    # 将所有DataFrame列表合并为一个大的DataFrame
    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\n文件合并完毕。总行数: {len(combined_df)}")

    # 3. 检查 'Subject' 列是否存在
    if 'Subject' not in combined_df.columns:
        print("错误：合并的数据中未找到 'Subject' 列。请检查CSV文件的表头是否正确。")
        return

    # 4. 按 'Subject' 列进行分组
    grouped = combined_df.groupby('Subject')

    print(f"按 'Subject' 分组完成。共找到 {len(grouped)} 个唯一的Subject。")

    # 5. 遍历所有分组并分别保存为新的CSV文件
    print("开始生成分类文件...")

    output_prefix = "arabicmmlu"

    for subject, group_df in grouped:
        # 处理 Subject 名称，使其适用于文件名
        # (例如，将 "Islamic Studies" 替换为 "Islamic_Studies")
        # 并处理可能的 None/NaN 值
        if pd.isna(subject):
            safe_subject_name = "Uncategorized" # 为空的Subject指定一个名字
        else:
            safe_subject_name = str(subject).replace(' ', '_').replace('/', '_').replace('\\', '_')

        output_filename = f"{output_prefix}_{safe_subject_name}.csv"

        try:
            # index=False: 不将pandas的索引（0, 1, 2...）写入CSV文件
            # encoding='utf-8-sig': 确保UTF-8编码，'sig' (BOM) 有助于Excel正确打开，
            # 尤其是处理像阿拉伯语这样的非英文字符时。
            group_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"  -> 已生成: {output_filename} (包含 {len(group_df)} 行)")
        except Exception as e:
            print(f"  -> 写入 {output_filename} 时出错: {e}")

    print("\n所有处理已完成。")

if __name__ == "__main__":
    combine_and_split_by_subject()
