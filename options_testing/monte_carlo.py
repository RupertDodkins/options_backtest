import numpy as np

def iterate_strategy(strategy, df, offsets):
    offset_results = []
    for offset in offsets:
        offset_result = strategy(df, offset)
        offset_results.append(offset_result)
    return offset_results
