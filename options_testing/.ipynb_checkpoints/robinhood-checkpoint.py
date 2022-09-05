import pandas as pd

def get_options_plays(transactions_file_loc='~/Downloads/RHTradeHistory (1).csv'):
    df = get_parsed_history(transactions_file_loc)
    option_plays = create_option_plays(df)

def parse_type(symbol_col):
    symbol_df = pd.DataFrame(index=symbol_col.index, columns=['ticker', 'strike', 'option_type', 'expiration'])
    for i in range(len(symbol_col)):
        parsed_data = symbol_col.iloc[i].split(' ')
        # if not np.all(np.array(parsed_data) == 'TSLA'):
        symbol_df.iloc[i] = parsed_data
    return symbol_df

def parse_action(action_col):
    action_df = pd.DataFrame(index=action_col.index, columns=['transaction', 'state'])
    for i in range(len(action_col)):
        parsed_data = action_col.iloc[i].split('T')
        action_df.iloc[i] = parsed_data
    return action_df

def expand_df(df):
    expanded_df = pd.DataFrame(index=np.arange(np.sum(df['quantity']), dtype=np.int), columns=df.columns)
    exp_ind = 0
    for ind, df_row in df.iterrows():
        quantity = int(df_row['quantity'])
        df_row['quantity'] = 1.
        expanded_df.iloc[exp_ind:exp_ind+quantity] = df_row
        # expanded_df.iloc[exp_ind:exp_ind+quantity]['quantity'] = 1.0
        exp_ind += quantity
    return expanded_df

def get_parsed_history(transactions_file_loc):
    df = pd.read_csv(transactions_file_loc, index_col=False)
    df = df[df['type'] == 'option']
    symbol_df = parse_type(df['symbol'])
    action_df = parse_action(df['action'])
    df = pd.concat((df, symbol_df, action_df), axis=1)
    df = df.drop(labels=['type', 'symbol', 'fees', 'ticker', 'details ', 'action', 'amount'], axis=1)
    df = df.loc[::-1].reset_index(drop=True)
    df = expand_df(df)
    return df

def create_option_plays(df):
    option_opens = df[df['state'] == 'O'].reset_index(drop=True)
    option_closes = df[df['state'] == 'C'].reset_index(drop=True)
    option_plays = pd.DataFrame(index=np.arange(len(option_opens)),
                                columns=['open', 'close', 'expiration', 'strike', 'option_type', 'quantity', 'filled',
                                         'closed', 'P/L'])
    for ind, row in option_opens.iterrows():
        option_plays.iloc[ind] = list(row[['date']]) + [0] + list(
            row[['expiration', 'strike', 'option_type', 'quantity', 'price']]) + [np.nan, 0]
        if row['transaction'] == 'B':
            option_plays.iloc[ind]['filled'] *= -1

    name_list = ['strike', 'option_type', 'expiration']
    for ind, play_row in option_plays.iterrows():
        match_ind = (option_closes[name_list] == play_row[name_list]).all(axis=1)
        matched_df = option_closes.loc[match_ind]
        if len(matched_df) > 0:
            option_plays.iloc[ind]['close'] = matched_df.iloc[0]['date']
            option_plays.iloc[ind]['closed'] = matched_df.iloc[0]['price']
            if matched_df.iloc[0]['transaction'] == 'S':
                option_plays.iloc[ind]['closed'] *= -1
            option_closes = option_closes.drop(matched_df.index[0], axis=0)

    option_plays['P/L'] = option_plays['filled'] - option_plays['closed']
    return option_plays

if __file__ == '__main__':
    option_plays = create_option_plays()
    option_plays['P/L'].cumsum().plot()


