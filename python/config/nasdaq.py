"""
nasdaq.py - nasdaq settings

"""

force_download = False
source_url = (
    "https://datahub.io/core/nasdaq-listings/_r/-/data/nasdaq-listed-symbols.csv"
)
work_directory = "../intermediate_data/nasdaq"
original_file_name = "nasdaq-listed-symbols"
result_file_name = f"{original_file_name}-clean"
pkl_file_name = f"{result_file_name}.pkl"
compare_words = 3
compare_case_sensitive = True
add_dollar_sign = True
