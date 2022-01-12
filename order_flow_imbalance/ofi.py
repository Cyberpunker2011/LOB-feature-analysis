import pandas as pd
import numpy as np
from tqdm import tqdm
import argparse
from datetime import datetime


parser = argparse.ArgumentParser()
parser.add_argument("--data", default='../data_cleaned/time_evolution_10_levels.csv', help="filename.", type=str)
parser.add_argument("--maxlevel", default=10, help="Maximum level of the book to study", type=int)
parser.add_argument("--time_delta", default=0.5, help="Time delta in seconds", type=float)
parser.add_argument("--acquisition_day", default='2020-04-06', help="First day of data acquisition in format YYYY-MM-DD", type=str)

def main(data, maxlevel, time_delta, acquisition_day):
    """
    Computes the order flow imbalance for each level of the book and 
    computes the corresponding evolution of mid price. 

    args:
        data: path to the dataframe containing the data, obtained by running 'deltas_computation.py'
        maxlevel: maximum level of the book to study
        time_delta: time delta in seconds to discretize time
        acquisition_day: first day of data acquisition in format YYYY-MM-DD
    """
    
    date_acquisition = int(datetime.fromisoformat(acquisition_day).timestamp())
    df = pd.read_csv(data)
    df = df.groupby('time', sort=False).agg(np.mean)
    df['time'] = df.index
    df.index = range(len(df))

    #clean datetime according to the date of acquisition
    df.drop (df[df['time']<date_acquisition].index, axis=0, inplace=True)
    df = df.sort_values(['time'], ignore_index=True)
    # #clean meaningless datetime, being sure that the last elment has the right length
    df.drop (df[[len(str((df['time'][i])))<len(str(list(df['time'])[-1])) for i in range(len(df))]].index, axis=0, inplace=True) 
    conversion = 1e9
    df['time_isoformat'] = df['time'].apply(lambda x: datetime.fromtimestamp(x/conversion))


    #computing the quantities delta V delta D
    for i in range(maxlevel):
        print('level {}'.format(i))

        check_bid_prices = np.diff (df['bid_price_{}'.format(i)])
        check_ask_prices = np.diff (df['ask_price_{}'.format(i)])
        delta_W = [0]
        delta_V = [0]

        j = 1
        # for furture improvement: this process can be optimized by employing .diff and masks 
        with tqdm(total=len(df)) as pbar:
            for bcheck, acheck in zip(check_bid_prices, check_ask_prices):

                if bcheck > 0:
                    delta_W.append(np.array(df['bid_volume_{}'.format(i)])[j])
                elif bcheck == 0:
                    delta_W.append(np.array(df['bid_volume_{}'.format(i)])[j] - \
                                np.array(df['bid_volume_{}'.format(i)])[j-1])
                else:
                    delta_W.append(- np.array(df['bid_volume_{}'.format(i)])[j-1])

                if acheck < 0:
                    delta_V.append(np.array(df['ask_volume_{}'.format(i)])[j])
                elif acheck == 0:
                    delta_V.append(np.array(df['ask_volume_{}'.format(i)])[j] - \
                                np.array(df['ask_volume_{}'.format(i)])[j-1])
                else:
                    delta_V.append(np.array(-df['ask_volume_{}'.format(i)])[j-1])
                j+=1
                pbar.update(1)

        df['delta_W_{}'.format(i)] = delta_W
        df['delta_V_{}'.format(i)] = delta_V
        df['e_{}'.format(i)] = df['delta_W_{}'.format(i)]-df['delta_V_{}'.format(i)]

    #drop row without a previous item, does  not make sense in .diff
    df.index = range(len(df))
    df.drop ([0], axis=0, inplace=True)
    df.to_csv('../data_cleaned/time_evolution_{}_levels_processed.csv'.format(maxlevel), index=False)


    time_delta = 1 #in seconds
    bin_edges = []
    df = df.sort_values(['time_isoformat'], ignore_index=True)
    t = df['time_isoformat'].iloc[0]

    from datetime import timedelta
    time_delta = timedelta(seconds=time_delta)
    while t <= df['time_isoformat'].iloc[-1] + time_delta:
        bin_edges.append(t)
        t = t + time_delta

    df['time_bin'] = pd.cut(df['time_isoformat'], bin_edges)
    nan_index = df.loc[pd.isna(df["time_bin"]), :].index[0]
    df = df.drop([nan_index], axis=0)
    df.index = range(len(df))


    bins = df['time_bin'].unique()

    mid_price_delta = []
    ofi = pd.DataFrame(bins, columns=['time_bin'])
    ofi['bin_label'] = np.arange(len(bins))

    for l in range(maxlevel): ofi['OFI_{}'.format(l)] = np.zeros(len(ofi))

    index = 0
    for b in bins:
        grouped = df[df['time_bin']==b]
        mid_price_delta.append(grouped['mid_price'].iloc[-1] - grouped['mid_price'].iloc[0])
        for l in range(maxlevel):
            ofi.iloc[index, l+2]= grouped['e_{}'.format(l)].sum()
        index += 1

    ofi['mid_price_delta'] = mid_price_delta

    ofi.to_csv('../data_cleaned/ofi_{}_levels.csv'.format(maxlevel), index=False)

if __name__ == "__main__":
    args = vars(parser.parse_args())
    main(**args)