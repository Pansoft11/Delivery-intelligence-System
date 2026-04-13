def calculate_utilization(df):
    return df.groupby('Engineer')['Hours'].sum()