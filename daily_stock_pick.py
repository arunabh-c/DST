#!/usr/bin/python
import urllib2
import csv
import math
import re
import time
import os
import smtplib
import json
import socket
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import datetime, timedelta
from Robinhood import Robinhood

my_trader = Robinhood();
my_trader.login(username="", password="")#!!!!!<<<<<<ADD ROBINHOOD USERNAME, PASSWORD HERE

start_seed = 1000.0
max_stx_to_hold = 5
stk_grwth_purchase_threshold = [0.09,1.0]#in %
total_5minute_intervals_to_check_avg_growth = 10 
new_stocks_found = []


with open('select_order.csv', 'rb') as f:
	    reader = csv.reader(f)
	    select_order = list(reader)

def get_stock_name(page_source):
		start = page_source.index("quote.ashx?t=") + len("quote.ashx?t=")
		end = page_source.index("&ty=c&p=d&b=1", start )
		return page_source[start:end]

def check_buy_opportunity(stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			todays_perf = my_trader.get_historical_quotes(stk,'5minute','day','regular')
			weeks_perf = my_trader.get_historical_quotes(stk,'5minute','week','regular')
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": check_buy_opportunity, " + str(stk) + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": check_buy_opportunity, " + str(stk) + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": check_buy_opportunity, " + str(stk) + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": check_buy_opportunity, " + str(stk) + " SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	todays_perf_size = 0
	avg_growth = 0.0
	buy_permit = False
	todays_perf_size = len(todays_perf['results'][0]['historicals'])
	weeks_perf_size = len(weeks_perf['results'][0]['historicals'])
	if todays_perf_size > 0:
		last_date_stamp = datetime.strptime(todays_perf['results'][0]['historicals'][todays_perf_size-1]['begins_at'], '%Y-%m-%dT%H:%M:%SZ').date()

		if todays_perf_size > 11 and last_date_stamp == datetime.now().date():#Avg. % growth of last 50 minutes
			close_price_right_now = float(todays_perf['results'][0]['historicals'][todays_perf_size-1]['close_price'])
			yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-1]['close_price'])
			day_before_yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-79]['close_price'])
			day_before_day_before_yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-157]['close_price'])
			perf_today = 100.0 * (close_price_right_now - yesterday_close_price)/yesterday_close_price
			perf_yesterday = 100.0 * (yesterday_close_price - day_before_yesterday_close_price)/day_before_yesterday_close_price
			perf_day_before_yesterday = 100.0 * (day_before_yesterday_close_price - day_before_day_before_yesterday_close_price)/day_before_day_before_yesterday_close_price
			for i in range(0,total_5minute_intervals_to_check_avg_growth):
				avg_growth = avg_growth + 10.0*(float(todays_perf['results'][0]['historicals'][todays_perf_size-1-i]['close_price']) - float(todays_perf['results'][0]['historicals'][todays_perf_size-2-i]['close_price']))/(float(todays_perf['results'][0]['historicals'][todays_perf_size-2-i]['close_price']))

			if  (perf_today <= stk_grwth_purchase_threshold[0] or perf_yesterday <= stk_grwth_purchase_threshold[0]) and (perf_yesterday <= stk_grwth_purchase_threshold[0] or perf_day_before_yesterday <= stk_grwth_purchase_threshold[0]) and (avg_growth >= stk_grwth_purchase_threshold[0] and avg_growth <= stk_grwth_purchase_threshold[1]):
				print (str(datetime.now()) + " Stock ready to be purchased: " + stk)
				print (str(datetime.now()) + " Performance today for " + stk + ": " + str(perf_today))
				print (str(datetime.now()) + " Performance yesterday for " + stk + ": " + str(perf_yesterday))
				print (str(datetime.now()) + " Performance day before yesterday for " + stk + ": " + str(perf_day_before_yesterday))
				print (str(datetime.now()) + " Last " + str(5*total_5minute_intervals_to_check_avg_growth) + " minutes growth for " + stk + ": " + str(avg_growth))

				buy_permit = True
	return buy_permit

def check_sell_opportunity(stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			todays_perf = my_trader.get_historical_quotes(stk,'5minute','day','regular')
			weeks_perf = my_trader.get_historical_quotes(stk,'5minute','week','regular')
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": check_sell_opportunity, " + str(stk) + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": check_sell_opportunity, " + str(stk) + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": check_sell_opportunity, " + str(stk) + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": check_sell_opportunity, " + str(stk) + " SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	avg_growth = 0.0
	sale_permit = False
	todays_perf_size = len(todays_perf['results'][0]['historicals'])
	weeks_perf_size = len(weeks_perf['results'][0]['historicals'])
	if todays_perf_size > 0:
		last_date_stamp = datetime.strptime(todays_perf['results'][0]['historicals'][todays_perf_size-1]['begins_at'], '%Y-%m-%dT%H:%M:%SZ').date()

		if todays_perf_size > 11 and last_date_stamp == datetime.now().date():#Avg. % growth of last 50 minutes
			close_price_right_now = float(todays_perf['results'][0]['historicals'][todays_perf_size-1]['close_price'])
			yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-1]['close_price'])
			day_before_yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-79]['close_price'])
			day_before_day_before_yesterday_close_price = float(weeks_perf['results'][0]['historicals'][weeks_perf_size-todays_perf_size-157]['close_price'])
			perf_today = 100.0 * (close_price_right_now - yesterday_close_price)/yesterday_close_price
			perf_yesterday = 100.0 * (yesterday_close_price - day_before_yesterday_close_price)/day_before_yesterday_close_price
			perf_day_before_yesterday = 100.0 * (day_before_yesterday_close_price - day_before_day_before_yesterday_close_price)/day_before_day_before_yesterday_close_price
			for i in range(0,total_5minute_intervals_to_check_avg_growth):
				avg_growth = avg_growth + 10.0*(float(todays_perf['results'][0]['historicals'][todays_perf_size-1-i]['close_price']) - float(todays_perf['results'][0]['historicals'][todays_perf_size-2-i]['close_price']))/(float(todays_perf['results'][0]['historicals'][todays_perf_size-2-i]['close_price']))
			if  (perf_today >= stk_grwth_purchase_threshold[0] or perf_yesterday >= stk_grwth_purchase_threshold[0]) and (perf_yesterday >= stk_grwth_purchase_threshold[0] or perf_day_before_yesterday >= stk_grwth_purchase_threshold[0]) and (avg_growth <= -stk_grwth_purchase_threshold[0] and avg_growth >= -stk_grwth_purchase_threshold[1]):
				print (str(datetime.now()) + " Stock ready to be sold: " + stk)
				print (str(datetime.now()) + " Performance today for " + stk + ": " + str(perf_today))
				print (str(datetime.now()) + " Performance yesterday for " + stk + ": " + str(perf_yesterday))
				print (str(datetime.now()) + " Performance day before yesterday for " + stk + ": " + str(perf_day_before_yesterday))
				print (str(datetime.now()) + " Last " + str(5*total_5minute_intervals_to_check_avg_growth) + " minutes growth for " + stk + ": " + str(avg_growth))

				sale_permit = True
	return sale_permit
	
def replace_parameter(old_param, new_param, url):
	init_url = url
	repl = re.subn(old_param, new_param, url)
	url = repl[0]
	replace_count = repl[1]
	return url, init_url, replace_count

def purchase_logger(stock, quantity, stock_price, free_cash):
	
	global max_stx_to_hold
	file_write_array = [str(datetime.now().strftime("%Y-%m-%d %H:%M")),stock, str(quantity), str(stock_price), str(free_cash)]
	trade_history = (os.stat('daily_last_state.txt').st_size != 0)

	if trade_history == False:
		f = open('daily_last_state.txt', 'w')
		for j in range(0,len(file_write_array)):
			if j == 4:
				f.write(file_write_array[j])
			else:
				f.write(file_write_array[j] + '\n')
	else:
		row_counter = 0
		file_lines = ["","","","",""]
		with open('daily_last_state.txt', 'r') as f:
			for line in f:
				if row_counter == 4:
					file_lines[row_counter] = file_write_array[row_counter]
				else:
					file_lines[row_counter] = line
					file_lines[row_counter] = (file_lines[row_counter].rstrip('\n') + ',' + file_write_array[row_counter] + '\n')
				row_counter = row_counter + 1

		with open('daily_last_state.txt', 'w') as f:
			f.writelines(file_lines) 
	f.close()

def sale_logger(free_cash, stk_to_sell_idx, total_count):	
		row_counter = 0
		file_lines = ["","","","",""]
		with open('daily_last_state.txt', 'r') as f:
			for line in f:
				if row_counter == 4:
					file_lines[row_counter] = str(free_cash)
				else:
					mylist = line.rstrip('\n').split(",")
					del mylist[stk_to_sell_idx]
					file_lines[row_counter] = ",".join([str(item) for item in mylist]) + '\n'
				row_counter = row_counter + 1

		with open('daily_last_state.txt', 'w') as f:
			f.writelines(file_lines) 
		f.close()
	
def send_email(message):
	fromaddr = ""#!!!!!<<<<<<ADD GMAIL ADDRESS HERE
	toaddr = ""#!!!!!<<<<<<ADD GMAIL ADDRESS HERE
	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddr
	msg['Subject'] = "Stock Activity"

	msg.attach(MIMEText(message, 'plain'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(fromaddr, "")#!!!!!<<<<<<ADD GMAIL PASSWORD HERE
	text = msg.as_string()
	server.sendmail(fromaddr, toaddr, text)
	server.quit()
	
def last_state_reader():
		global start_seed, my_trader
		holdings_array = [[], [], [], []]
		last_purchase_time = []
		last_stock = []
		last_stock_quantity = []
		last_stock_purchase_price = []
		f = open('daily_last_state.txt', 'r')		
		try:
			row_counter = 0
			for line in f:
				if row_counter < 4:
					holdings_array[row_counter] = (line.rstrip('\n')).split(",")
				if row_counter == 4:
					free_cash = float(line.rstrip('\n'))
				row_counter = row_counter + 1
		finally:
			f.close()		    	
		if len(holdings_array[0]) > 0:
			last_stock = holdings_array[1]
			new_balance = free_cash
			for j in range(0,len(holdings_array[0])):
				last_purchase_time.append(datetime.strptime(holdings_array[0][j], "%Y-%m-%d %H:%M"))   
				last_stock_quantity.append(float(holdings_array[2][j]))
				last_stock_purchase_price.append(float(holdings_array[3][j]))
				last_stock_present_price = 0.0
				exec_flag = False
				try_counter = 0
				while exec_flag == False and try_counter < 10:
					try:
						last_stock_present_price = float(my_trader.last_trade_price(last_stock[j]))
						exec_flag = True
					except ValueError, e:
						print ((str(datetime.now()) + ": last_state_reader, " + last_stock[j] + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
						print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
						try_counter = try_counter + 1
						time.sleep(10)
					except urllib2.HTTPError, e:
						print ((str(datetime.now()) + ": last_state_reader, " + last_stock[j] + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
						print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
						try_counter = try_counter + 1
						time.sleep(10)
					except urllib2.URLError, e:
						print ((str(datetime.now()) + ": last_state_reader, " + last_stock[j] + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
						print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
						try_counter = try_counter + 1
						time.sleep(10)
					except socket.error, e:
						print (str(datetime.now()) + ": last_state_reader, " + last_stock[j] + " SocketError: \ne: " + str(e))
						print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
						try_counter = try_counter + 1
						time.sleep(10)

				if last_stock_present_price > 0.0:
					new_balance = new_balance + last_stock_quantity[j] * last_stock_present_price
					gains_since_stk_purchase = 100.0*(last_stock_present_price - last_stock_purchase_price[j])/last_stock_purchase_price[j]
					print (str(datetime.now()) + ": Stock holding: " + last_stock[j] + " purchased on " + str(last_purchase_time[j]) + ", Gain since last purchase: " + str(gains_since_stk_purchase) + "%")

			gains_since_beginning = 100.0*(new_balance - start_seed)/start_seed
			print ("Net Gain since beginning: " + str(gains_since_beginning) + "%")
			print ("Latest Balance: " + str(new_balance))
		else:
			new_balance = start_seed
			free_cash = start_seed

		return last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance

def time_to_sleep():
	day = datetime.now().isoweekday()
	hour =  datetime.now().hour
	minute = datetime.now().minute
	second = datetime.now().second
	tts = 300
	if (day in range(1,6)) and (hour in range(8,14)):#mon-fri 830am-3pm, run every 5 minutes
		tts = 300
	elif (day in range(1,6)) and (hour > 14):#mon-fri 3pm-12am, sleep till 830 am
		tts = (32 - hour)*3600 - minute*60 - second + 1800
	elif (day in range(1,6)) and (hour < 8):#mon-fri pre-8am, sleep till 830 am
		tts = (8-hour)*3600 - minute*60 - second + 1800
	elif (day > 5):#weekend, sleep till monday 830am
		tts = (7-day)*24*3600 + (32-hour)*3600 - minute*60 - second + 1800
	if tts > 300:
		_, _, _, _, _, _ = last_state_reader()
		d = datetime(1,1,1) + timedelta(seconds=tts)
		#print("Sleeping for ")
		#print("%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second))
		d = datetime.now() + timedelta(seconds=tts)
		print("Wake up at " + d.strftime("%A"))
		print("%d:%d:%d" % (d.hour, d.minute, d.second))
	return tts

def purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, final_stock):
	global max_stx_to_hold, my_trader, new_stocks_found

	final_stock_price = 0.0
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			final_stock_price = float(my_trader.last_trade_price(final_stock))
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": purchase_accounting, " + final_stock + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": purchase_accounting, " + final_stock + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": purchase_accounting, " + final_stock + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": purchase_accounting, " + final_stock + " SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	if final_stock_price > 0.0 and math.floor(free_cash/final_stock_price) > 0:
		if len(last_stock) < max_stx_to_hold:
			available_cash = free_cash/(max_stx_to_hold - len(last_stock))
		else: 
			available_cash = free_cash
		total_stocks = math.floor(available_cash/final_stock_price)
		if total_stocks > 0.0:
			final_purchase_amount = final_stock_price * total_stocks
			free_cash = free_cash - final_purchase_amount

			purchase_logger(final_stock, total_stocks, final_stock_price, free_cash)
			print (str(datetime.now()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount))
			with open('daily_activity_log.txt', 'a`') as f:
				f.writelines(str(datetime.now()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount) + '\n')
			send_email(str(datetime.now()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount))
			print (str(datetime.now()) + " Free cash left: " + str(free_cash))
			if final_stock in new_stocks_found:#Remove purchased stock from new_stocks_found
				new_stocks_found.remove(final_stock)
		else:
			print ("Not enough cash left to buy " + final_stock)
			
def sale_accounting(stk, count, purchase_price, free_cash, stk_idx):
	sale_price = 0.0
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			sale_price = float(my_trader.last_trade_price(stk[stk_idx]))
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": sale_accounting, " + stk[stk_idx] + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": sale_accounting, " + stk[stk_idx] + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": sale_accounting, " + stk[stk_idx] + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": sale_accounting, " + stk[stk_idx] + " SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	if sale_price > 0.0:
		free_cash = free_cash + float(count) * sale_price
		sale_logger(free_cash, stk_idx, len(stk))

		sale_gain = 100.0*(sale_price-purchase_price)/purchase_price
		print (str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		with open('daily_activity_log.txt', 'a`') as f:
			f.writelines(str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain) + '\n')
		send_email(str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		print (str(datetime.now()) + " Free cash left: " + str(free_cash))

def result_check(url,last_stock,free_cash):
	global my_trader, new_stocks_found
	page_source = ""
	
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			response = urllib2.urlopen(url)
			page_source = response.read()
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": Result Check, ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": Result Check, HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": Result Check, URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": Result Check, SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	stock = []
	prefix ="quote.ashx?t="

	for i in range (0,int(page_source.count(prefix)/11)):
		stk = get_stock_name(page_source)
		for i in range(0,11):
			page_source = page_source.replace(str("quote.ashx?t=" + stk + "&ty=c&p=d&b=1"),"")#Delete first stock from page source string to arrive at next stock

		exec_flag = False
		try_counter = 0
		while exec_flag == False and try_counter < 10:
			try:
				final_stock_price = float(my_trader.last_trade_price(stk))
				if final_stock_price <= free_cash:#Proceed only if stock price lower than available cash
					if stk not in new_stocks_found:
						json_obj = my_trader.instruments(stk)
						stk_tradeable_on_robinhood = str(json_obj[0]['tradeable'])			
						if stk_tradeable_on_robinhood == "True" and stk not in last_stock:#Proceed only if stock tradeable on robinhood
							stock.append(stk)
					elif stk not in last_stock:
							stock.append(stk)
				exec_flag = True
			except ValueError, e:
					print ((str(datetime.now()) + ": Result Check, " + str(stk) + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
					print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
					try_counter = try_counter + 1
					time.sleep(10)
			except urllib2.HTTPError, e:
					print ((str(datetime.now()) + ": Result Check, " + str(stk) + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
					print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
					try_counter = try_counter + 1
					time.sleep(10)
			except urllib2.URLError, e:
					print ((str(datetime.now()) + ": Result Check, " + str(stk) + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
					print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
					try_counter = try_counter + 1
					time.sleep(10)
			except socket.error, e:
					print (str(datetime.now()) + ": Result Check, " + str(stk) + " SocketError: \ne: " + str(e))
					print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
					try_counter = try_counter + 1
					time.sleep(10)

	return stock

def get_param_val(param, end, page_source):
		start = page_source.index(param) + len(param)
		end = page_source.index(end, start)
		if page_source[start:end][0] == '<':
			start = start + 29
			end = end - 7
		if page_source[start:end][len(page_source[start:end])-1] == '%':
			end = end - 1
		if page_source[start:end] != "-":
			return_val = float(page_source[start:end])
		else:
			return_val = None
		return return_val

def check_stk_sale(stk):
	sale_flag = False
	page_source = ""
	
	exec_flag = False
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			response = urllib2.urlopen("http://finviz.com/quote.ashx?t=" + stk + "&ty=c&p=d&b=1")
			page_source = response.read()
			exec_flag = True
		except ValueError, e:
			print ((str(datetime.now()) + ": check_stk_sale, " + stk + " ValueError: " + str(ValueError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.HTTPError, e:
			print ((str(datetime.now()) + ": check_stk_sale, " + stk + " HTTPError: " + str(Urllib2.HTTPError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except urllib2.URLError, e:
			print ((str(datetime.now()) + ": check_stk_sale, " + stk + " URLError: " + str(urllib2.URLError)) + "\ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
		except socket.error, e:
			print (str(datetime.now()) + ": check_stk_sale, " + stk + " SocketError: \ne: " + str(e))
			print (str(datetime.now()) + " " + str(try_counter) + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)

	RSI = get_param_val('RSI (14)</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
	Recom = get_param_val('">Recom</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
	if Recom > 2.8 or RSI > 65:
		SMA20 = get_param_val('">SMA20</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		SMA50 = get_param_val('">SMA50</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		Perf_week = get_param_val('">Perf Week</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		Perf_month = get_param_val('">Perf Month</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		if SMA20 > stk_grwth_purchase_threshold[0] or SMA50 > stk_grwth_purchase_threshold[0] or Perf_week > stk_grwth_purchase_threshold[0] or Perf_month > stk_grwth_purchase_threshold[0]: 
			sale_flag = True
	return sale_flag

def optimize(last_stock,last_purchase_time,free_cash):
	global max_stx_to_hold
	allowed_stk_cnt = 0
	url = "http://finviz.com/screener.ashx?v=111&f=an_recom_holdbetter,fa_debteq_u1,fa_epsqoq_high,fa_netmargin_o5,fa_pe_u10,fa_quickratio_o1,fa_roe_pos,ta_perf_1wdown,ta_perf2_4wdown,ta_rsi_os40,ta_sma20_pb,ta_sma200_pb,ta_sma50_pb&ft=4&ar=180"
	prev_url = url
	repl_count = 0	
	tmp_stock = []
	select_order_index = 0
	
	if len(last_stock) < max_stx_to_hold:
		allowed_stk_cnt = allowed_stk_cnt + max_stx_to_hold - len(last_stock)
	
	tmp_stock = result_check(url,last_stock,free_cash)
	while len(tmp_stock) > 1 and select_order_index < len(select_order):
		filter_success_flag = False
		if len(tmp_stock) > 1:
			url, prev_url, repl_count = replace_parameter(select_order[select_order_index][0],select_order[select_order_index][1], url)
			tmp_stock = result_check(url,last_stock,free_cash)
			filter_success_flag = True
		if tmp_stock == None or len(tmp_stock) < 1:
			url = prev_url
			tmp_stock = result_check(url,last_stock,free_cash)
			filter_success_flag = False
		'''if filter_success_flag == True and repl_count == 1:
			print ("Filtered on " + select_order[select_order_index][2])'''
		select_order_index = select_order_index + 1
	return tmp_stock

if __name__ == '__main__':
	print ("Starting Loop..")
	last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader() 
	new_stocks_start_time = datetime.now()
	while True:
		start_time = datetime.now()
		if (datetime.now() - new_stocks_start_time).days > 30.0:#Refresh new_stocks_found array every 30 days to remove stale stocks
			new_stocks_found = []
			new_stocks_start_time = datetime.now()
		if (datetime.now().isoweekday() in range(1,6)) and datetime.now().time() > datetime.strptime('8:29','%H:%M').time() and datetime.now().time() < datetime.strptime('15:01','%H:%M').time():
			final_stock = optimize(last_stock,last_purchase_time, free_cash)

			for i in range(0,len(last_stock)):#Check if any stocks ready for sale
				if i < len(last_stock):
					if datetime.now().date() != last_purchase_time[i].date() and check_stk_sale(last_stock[i]):
						if check_sell_opportunity(last_stock[i]):
							sale_accounting(last_stock, last_stock_quantity[i], last_stock_purchase_price[i], free_cash, i)
							last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader()

			for i in range(0,len(final_stock)):#Check if any stocks ready for purchase
				if final_stock[i] not in new_stocks_found:
					print(str(datetime.now()) + ": New stock found: " + str(final_stock[i]))
					new_stocks_found.append(final_stock[i])
				if check_buy_opportunity(final_stock[i]):
					purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, final_stock[i])
					last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader()

		sleep_duration = time_to_sleep()
		compute_time = (datetime.now() - start_time).seconds + (datetime.now() - start_time).microseconds/1000000.0
		time.sleep(sleep_duration-compute_time)
		if sleep_duration > 300:
			print datetime.now().date()