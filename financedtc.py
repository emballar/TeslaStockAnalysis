#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 13:54:21 2024

@author: erinballar
"""

import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

stock = 'TSLA'
headers = {'User-Agent' : 'erinballar619@gmail.com'}
# '10': {'cik_str': 1318605, 'ticker': 'TSLA', 'title': 'Tesla, Inc.'}

companytickers = requests.get("https://www.sec.gov/files/company_tickers.json",
headers=headers)
companyCIK = pd.DataFrame.from_dict(companytickers.json(), orient = "Index")
companyCIK['cik_str']= companyCIK['cik_str'].astype(str).str.zfill(10)


cik = companyCIK[10:11].cik_str[0]
companyfiling = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json',
headers=headers)
allFilings = pd.DataFrame.from_dict(companyfiling.json()['filings']['recent'])
companyFacts = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=headers)

#look at what us-gaap columns we can use
x = pd.DataFrame(companyFacts.json()['facts']['us-gaap'].keys())

#revenues
revenues_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['Revenues']['units']['USD'])
revenues_dataframe = revenues_dataframe[revenues_dataframe.frame.notna()]
revenuesdf = revenues_dataframe[revenues_dataframe['form'] == '10-K']

revenues = revenuesdf.copy()

revenues['start'] = pd.to_datetime(revenues['start'])
revenues['end'] = pd.to_datetime(revenues['end'])
revenues.loc[:, 'duration'] = (revenues['end'] - revenues['start']).dt.days
# Filter the DataFrame based on the duration (get rid of filings that only accountfor a few months)
revenues = revenues[(revenues['duration'] >= 330) &
(revenues['duration'] <= 370)].reset_index(drop=True)
revenues = revenues.drop('duration', axis = 1)
revenues['start'] = revenues['start'].dt.strftime('%Y-%m-%d')
revenues['end'] = revenues['end'].dt.strftime('%Y-%m-%d')


#inventory
inventory_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['InventoryNet']['units']['USD'])
inventory_dataframe = inventory_dataframe[inventory_dataframe.frame.notna()]
inventory = inventory_dataframe[inventory_dataframe['form'] == '10-K']

#cost of goods sold
cogs_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['CostOfGoodsSold']['units']['USD'])
cogs_dataframe = cogs_dataframe[cogs_dataframe.frame.notna()]
cogs = cogs_dataframe[cogs_dataframe['form'] == '10-K']

#assets

assets_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['Assets']['units']['USD'])
assets_dataframe = assets_dataframe[assets_dataframe.frame.notna()]
assets = assets_dataframe[assets_dataframe['form'] == '10-K']

#liabilities
liabilities_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['Liabilities']['units']['USD'])
liabilities_dataframe = liabilities_dataframe[liabilities_dataframe.frame.notna()]
liabilities = liabilities_dataframe[liabilities_dataframe['form'] == '10-K']

#net profit
np_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['NetIncomeLoss']['units']['USD'])
np_dataframe = np_dataframe[np_dataframe.frame.notna()]
netprofitdf = np_dataframe[np_dataframe['form'] == '10-K']

netprofit = netprofitdf.copy()

netprofit['start'] = pd.to_datetime(netprofit['start'])
netprofit['end'] = pd.to_datetime(netprofit['end'])
netprofit.loc[:, 'duration'] = (netprofit['end'] - netprofit['start']).dt.days
# Filter the DataFrame based on the duration (get rid of filings that only accountfor a few months)
netprofit = netprofit[(netprofit['duration'] >= 330) &
(netprofit['duration'] <= 370)].reset_index(drop=True)
netprofit = netprofit.drop('duration', axis = 1)
netprofit['start'] = netprofit['start'].dt.strftime('%Y-%m-%d')
netprofit['end'] = netprofit['end'].dt.strftime('%Y-%m-%d')

#equity
# equity = assets - liabilities
equity = pd.merge(assets, liabilities, on = 'end')
equity['Equity'] = equity['val_x'] - equity['val_y']
equity.rename(columns={'val_x': 'assets', 'val_y': 'liabilities'}, inplace=True)

#current assets
curassets_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['AssetsCurrent']['units']['USD'])
curassets_dataframe = curassets_dataframe[curassets_dataframe.frame.notna()]
curassets = curassets_dataframe[curassets_dataframe['form'] == '10-K']

#current liabilities
curliabilities_dataframe = pd.DataFrame(companyFacts.json()['facts']['us-gaap']
['LiabilitiesCurrent']['units']['USD'])
curliabilities_dataframe = curliabilities_dataframe[curliabilities_dataframe.frame.notna()]
curliabilities = curliabilities_dataframe[curliabilities_dataframe['form'] == '10-K']

#ratios:
#asset turnover : asset

revenues = revenues.drop(revenues.index[0])
at = pd.merge(revenues, assets, on = 'end')
at['beginning_assets'] = at['val_y'].shift()
at = at.rename(columns = {'val_x' : 'Revenue', 'val_y': 'ending_assets'})
at["AssetTurnover"] = at['Revenue'] / ((at["beginning_assets"] + at["ending_assets"]) / 2)
at = at.dropna()


#return on equity : net profit, equity

netprofit = netprofit.drop(netprofit.index[0])
equity = equity.rename(columns = {'end_x' : 'end'})
roe = pd.merge(netprofit, equity, on = 'end')
roe['beginning_equity'] = roe['Equity'].shift()
roe = roe.rename(columns = {'val' : 'netprofit', 'Equity': 'ending_equity'})
roe["ReturnOnEquity"] = roe["netprofit"] / ((roe["beginning_equity"] + roe["ending_equity"]) / 2)
roe = roe.dropna()

#net profit margin: netprofit, revenue

npm = pd.merge(netprofit, revenues, on = 'end')
npm['NetProfitMargin'] = (npm['val_x']/npm['val_y']) * 100

npm = npm.rename(columns = {'end_x':'Date'})

#current ratio, current assets + liabilities

cr = pd.merge(curassets, curliabilities, on = 'end')
cr['CurrentRatio'] = (cr['val_x']/cr['val_y'])

#leverage: total assets/total equity -use of debt to buy assets

equity['leverage'] = equity['assets'] / equity['Equity']

#debt to equity: total debt / total equity

equity['debttoequity'] = equity['liabilities'] / equity['Equity']

equity = equity.rename(columns = {'end_x':'Date'})


# get stock price data
stock_data = yf.download(stock, start='2011-12-30', end='2024-01-10')

stock_data.reset_index(inplace=True)

stock_data.rename(columns={'index': 'Date'}, inplace=True)

stock_df = pd.DataFrame(stock_data)

stock_df = stock_df[['Date', 'Close']]

#filter to only stock price of first of the month
stock_df = stock_df[stock_df['Date'].dt.day == 1]


equity['end'] = pd.to_datetime(equity['end'])
stock_df['Date'] = pd.to_datetime(stock_df['Date'])
npm['end'] = pd.to_datetime(npm['end'])
roe['end'] = pd.to_datetime(roe['end'])
at['end'] = pd.to_datetime(at['end'])
cr['end'] = pd.to_datetime(cr['end'])

############
#graphs

color1 = "#373737"
color2 = "#A02316"

#Stock Price v. Asset Turnover
fig5, ax1 = plt.subplots(figsize=(8, 8))
ax2 = ax1.twinx()


line9, = ax1.plot(stock_df['Date'], stock_df['Close'], color=color1, label = 'Stock Price')

line10, = ax2.plot(at['end'], at['AssetTurnover'], color=color2, label = 'Asset Turnover Ratio')

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)

ax2.set_ylabel("Asset Turnover Ratio", color=color2, fontsize=14)
ax2.tick_params(axis="y", labelcolor=color2)

fig5.suptitle("Tesla Stock Price v. Asset Turnover Ratio", fontsize=20)
fig5.autofmt_xdate()

lines = [line9, line10]
labels = [line.get_label() for line in lines]

fig5.legend(lines, labels, bbox_to_anchor=(.90, .30))

plt.show()

#Stock Price v.Return On Equity
fig4, ax1 = plt.subplots(figsize=(8, 8))
ax2 = ax1.twinx()


line7, = ax1.plot(stock_df['Date'], stock_df['Close'], color=color1, label = 'Stock Price')

line8, =ax2.plot(roe['end'], roe['ReturnOnEquity'], color=color2, label = 'Return On Equity')

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)

ax2.set_ylabel("Return On Equity", color=color2, fontsize=14)
ax2.tick_params(axis="y", labelcolor=color2)

fig4.suptitle("Tesla Stock Price v. Return On Equity", fontsize=20)
fig4.autofmt_xdate()

lines = [line7, line8]
labels = [line.get_label() for line in lines]

fig4.legend(lines, labels, bbox_to_anchor=(.90, .30))

plt.show()

#Stock Price v. NetProfitMargin
fig3, ax1 = plt.subplots(figsize=(8, 8))
ax2 = ax1.twinx()


line5, = ax1.plot(stock_df['Date'], stock_df['Close'], color=color1, label = 'Stock Price')


line6, = ax2.plot(npm['end'], npm['NetProfitMargin'], color=color2, label = 'Net Profit Margin')

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)

ax2.set_ylabel("Net Profit Margin", color=color2, fontsize=14)
ax2.tick_params(axis="y", labelcolor=color2)

fig3.suptitle("Tesla Stock Price v. Net Profit Margin", fontsize=20)
fig3.autofmt_xdate()


lines = [line5, line6]
labels = [line.get_label() for line in lines]

fig3.legend(lines, labels, bbox_to_anchor=(.90, .30))

plt.show()

#Stock Price v. Debt To Equity Ratio
fig, ax1 = plt.subplots(figsize=(8, 8))
ax2 = ax1.twinx()

line3, = ax1.plot(stock_df['Date'], stock_df['Close'], color=color1, label='Stock Price')
line4, = ax2.plot(equity['end'], equity['debttoequity'], color=color2, label='Debt To Equity Ratio')

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)

ax2.set_ylabel("Debt To Equity Ratio", color=color2, fontsize=14)
ax2.tick_params(axis="y", labelcolor=color2)

fig.suptitle("Tesla Stock Price v. Debt To Equity Ratio", fontsize=20)
fig.autofmt_xdate()

lines = [line3, line4]
labels = [line.get_label() for line in lines]

fig.legend(lines, labels, bbox_to_anchor=(.65, .87))

plt.show()

#Stock Price v. Current Ratio
fig2, ax1 = plt.subplots(figsize=(8, 8))
ax2 = ax1.twinx()


line1, = ax1.plot(stock_df['Date'], stock_df['Close'], color=color1, label='Stock Price')

line2, = ax2.plot(cr['end'], cr['CurrentRatio'], color=color2, label='Current Ratio')

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)

ax2.set_ylabel("Current Ratio", color=color2, fontsize=14)
ax2.tick_params(axis="y", labelcolor=color2)

lines = [line1, line2]
labels = [line.get_label() for line in lines]
fig2.legend(lines, labels, bbox_to_anchor=(.90, .30))

fig2.suptitle("Tesla Stock Price v. Current Ratio", fontsize=20)
fig2.autofmt_xdate()

plt.show()


#look at stock prices following elon buying twitter

stock_1y = yf.download(stock, start='2021-10-27', end='2023-10-27')

stock_1y.reset_index(inplace=True)

stock_1y.rename(columns={'index': 'Date'}, inplace=True)

stock_1y = pd.DataFrame(stock_1y)

stock_1y = stock_1y[['Date', 'Close']]


#graph
stock_1y['Date'] = pd.to_datetime(stock_1y['Date'])

fig6, ax1 = plt.subplots(figsize=(8, 8))

ax1.plot(stock_1y['Date'], stock_1y['Close'], color=color1)

ax1.set_xlabel("Date")
ax1.set_ylabel("Stock Price ($)", color=color1, fontsize=14)
ax1.tick_params(axis="y", labelcolor=color1)
plt.axvline(x= pd.to_datetime('2022-10-27'), color= color2, linestyle='--')

plt.text(stock_1y['Date'].iloc[260], # x-axis position
         stock_1y['Close'].iloc[1], # y-axis position
         'Elon Musk Acquires Twitter\n October 27, 2022', # text displayed
         fontsize=12,
         color= color2)

fig6.suptitle("Tesla Stock Price", fontsize=20)
plt.title("Before & After Elon Musk's Twitter Acquisition", fontsize=20)
fig6.autofmt_xdate()

plt.show()


