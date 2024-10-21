import io


def df_to_parquet(df):
    """
    Simple helper function to convert pandas dataframe to an in-memory parquet file
    :param df: pandas dataframe
    :return: parquet file as bytes
    """
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine='pyarrow')
    buffer.seek(0)
    return buffer.getvalue()
