#!/usr/bin/env python3

from piston.account import Account
from piston.storage import configStorage as config
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import sys

fmt = '%Y-%m-%dT%H:%M:%S'

account_name = "minnowbooster"
from_date = datetime.datetime(2017, 10, 7, 0, 0, 0, 0)
to_date = datetime.datetime(2017, 10, 22, 23, 59, 59, 9999)

exclude_ops = None
only_ops = ['transfer']

num_entries = 0
outgoing = []
open_refunds = []
incoming = []
incoming_accepted = []

refund_memos = ['Steem had problems', \
                'Sorry, we could not upvote', \
                'Your post is too old', \
                'quota of', \
                'our post link was invalid', \
                'Comment voting was disabled', \
                'You already voted on this post', \
                'You are banned', \
                'Your request could not be filled', \
                'Sorry, you need to send at least', \
                'We currently refuse to make business with you!', \
                'refund', \
                'Your memo is not in the required format', \
                'Minnowbooster is taking a quick nap', \
                'I tried upvoting you but the post was in its last 12 hours']

for entry in Account(account_name).rawhistory(
        limit = -1, only_ops = only_ops,
        exclude_ops = exclude_ops):
    num_entries += 1
    op_type = entry[1]["op"][0]
    op = entry[1]["op"][1]
    timestamp = datetime.datetime.strptime(entry[1]['timestamp'], fmt) # format: 2017-08-27T20:23:21'
    if timestamp < from_date:
        break
    if timestamp > to_date:
        continue

    if op_type == "transfer":
        amount = op['amount'].split(" ")
        if amount[1] == "STEEM": # only SBD
            continue
        sbd = float(amount[0])
        if op['from'] == account_name:
            is_refund = False
            for memo in refund_memos:
                if memo in op['memo']:
                    is_refund = True
                    break
            if is_refund:
                open_refunds.insert(0, {'timestamp': timestamp, 'sender':op['to'], 'value':sbd})
                outgoing.append({'timestamp': timestamp, 'sender':op['to'], 'value':sbd})

        elif op['to'] == account_name and ("https://" in op['memo'] or "@" in op['memo']):
            is_refund = False
            for refund in open_refunds:
                if op['from'] == refund['sender'] and sbd == refund['value']:
                    open_refunds.remove(refund)
                    is_refund = True
                    break
            if not is_refund:
                incoming_accepted.append({'timestamp': timestamp, 'sender':op['from'], 'value':sbd, 'memo':op['memo']})
            incoming.append({'timestamp': timestamp, 'sender':op['from'], 'value':sbd, 'memo':op['memo']})



datetimestamps = []
payments = []

for rx in incoming_accepted:
    datetimestamps.append(mdates.date2num(rx['timestamp']))
    payments.append(rx['value'])

prev_date = None
incoming_accepted_per_day = []
ts_incoming_accepted_per_day = []
daily_sum = 0
mb_gain_per_day = []
mb_daily_sum = 0
daily_mb_votes = []
daily_ext_votes = []
mb_votes = 0
ext_votes = 0
ext_daily_sum = 0
ext_payout_per_day = []

sell_your_vote_ann = datetime.datetime(2017, 10, 15, 16, 18, 0, 0)

for rx in incoming_accepted: # list entries in reverse time direction!
    date = rx['timestamp'].date()
    if prev_date and date != prev_date: # first entry from previous day
        incoming_accepted_per_day.append(daily_sum)
        mb_gain_per_day.append(mb_daily_sum)
        ts_incoming_accepted_per_day.append(mdates.date2num(prev_date) + 0.5)
        daily_ext_votes.append(ext_votes)
        daily_mb_votes.append(mb_votes)
        ext_payout_per_day.append(ext_daily_sum)
        daily_sum = 0
        mb_daily_sum = 0
        mb_votes = 0
        ext_votes = 0
        ext_daily_sum = 0
    daily_sum += rx['value']
    prev_date = date
    if rx['timestamp'] < sell_your_vote_ann or rx['value'] > 6:
        mb_daily_sum += rx['value']
        mb_votes += 1
    else:
        mb_daily_sum += 0.25 * rx['value']
        ext_daily_sum += 0.75 * rx['value']
        ext_votes += 1

incoming_accepted_per_day.append(daily_sum)
mb_gain_per_day.append(mb_daily_sum)
ts_incoming_accepted_per_day.append(mdates.date2num(prev_date) + 0.5)
daily_ext_votes.append(ext_votes)
daily_mb_votes.append(mb_votes)
ext_payout_per_day.append(ext_daily_sum)

prev_date = None
incoming_per_day = []
ts_incoming_per_day = []
daily_sum = 0
for rx in incoming:
    date = rx['timestamp'].date()
    if prev_date and date != prev_date: # next day
        incoming_per_day.append(daily_sum)
        ts_incoming_per_day.append(mdates.date2num(prev_date) + 0.5)
        daily_sum = 0
    daily_sum += rx['value']
    prev_date = date
incoming_per_day.append(daily_sum)
ts_incoming_per_day.append(mdates.date2num(prev_date) + 0.5)

xFmt = mdates.DateFormatter('%m/%d')

plt.figure(figsize=(12,6))
plt.semilogy(datetimestamps, payments, linestyle="none", marker=".", label="accepted payments")
plt.gcf().autofmt_xdate()
plt.gca().xaxis.set_major_formatter(xFmt)
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
plt.grid()
plt.xlabel("Date")
plt.ylabel("Fulfilled payments (SBD)")
plt.axvline(mdates.date2num(sell_your_vote_ann), color='orange', linestyle='dashed', linewidth=2, label="[ANN] Sell your vote")
plt.tight_layout()
plt.legend()
plt.show()

def shift_list(lst, off):
    return [t + off for t in lst]

plt.figure(figsize=(12,6))
plt.bar(shift_list(ts_incoming_accepted_per_day, -0.2), ext_payout_per_day, label="external user payouts", color="r", width=0.4, align='center')
plt.bar(shift_list(ts_incoming_accepted_per_day, +0.2), mb_gain_per_day, label="MB daily income", width=0.4, align='center')
plt.gcf().autofmt_xdate()
plt.gca().xaxis.set_major_formatter(xFmt)
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
plt.grid()
plt.xlabel("Date")
plt.ylabel("Daily sum of payments (SBD)")
plt.axvline(mdates.date2num(sell_your_vote_ann), color='orange', linestyle='dashed', linewidth=2, label="[ANN] Sell your vote")
plt.tight_layout()
plt.legend(loc=2)
plt.show()

plt.figure(figsize=(12,6))
plt.bar(shift_list(ts_incoming_accepted_per_day, -0.2), daily_ext_votes, align='center', width=0.4, label="external votes")
plt.bar(shift_list(ts_incoming_accepted_per_day, +0.2), daily_mb_votes, color='r', align='center', width=0.4, label="MB votes")
plt.gcf().autofmt_xdate()
plt.gca().xaxis.set_major_formatter(xFmt)
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
plt.axvline(mdates.date2num(sell_your_vote_ann), color='orange', linestyle='dashed', linewidth=2, label="[ANN] Sell your vote")
plt.tight_layout()
plt.legend(loc=4)
plt.grid()
plt.xlabel("date")
plt.ylabel("votes/day")
plt.show()
