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
import inspect
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import datetime, timedelta
from Robinhood import Robinhood

start_seed = 1000.0
max_stx_to_hold = 5
stk_grwth_purchase_threshold = [0.09,1.0]#in %
total_5minute_intervals_to_check_avg_growth = 10 
new_stocks_found = []


with open('select_order.csv', 'rb') as f:
		reader = csv.reader(f)
		select_order = list(reader)

with open('extra_filters.csv', 'rb') as f:
		reader = csv.reader(f)
		extra_filters = list(reader)

with open('banned_sectors.csv') as f:
		banned_sectors = f.readlines()
		banned_sectors = [x.strip() for x in banned_sectors]

with open('user_details.txt') as f:
		user_ids = f.readlines()
		user_ids = [x.strip() for x in user_ids]

with open('urls.txt') as f:
		init_url = f.readlines()
		init_url = [x.strip() for x in init_url]

my_trader = Robinhood();
my_trader.login(username=user_ids[0], password=user_ids[1])

def robinhood_calls(command, stk):
	exec_flag = False
	value_to_return = None
	try_counter = 0
	executable = "value_to_return = my_trader." + command
	while exec_flag == False and try_counter < 10:
		try:
			exec(executable)
			exec_flag = True
		except Exception:
			import traceback
			print (str(datetime.now()) + ' ***ROBINHOOD CALL EXCEPTION***: ' + stk + ", " + command + ", " + traceback.format_exc() + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
			if try_counter == 10:
				send_email(str(datetime.now()) + ": App crashed in func. robinhood calls while processing command: " + command + " for stock " + stk + " with error: " + traceback.format_exc())
	return value_to_return
		
def finviz_calls(url):
	exec_flag = False
	page_source = None
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			response = urllib2.urlopen(url)
			page_source = response.read()
			exec_flag = True
		except Exception:
			import traceback
			print (str(datetime.now()) + ' ***FINVIZ CALL EXCEPTION***: ' + traceback.format_exc() + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
			if try_counter == 10:
				send_email(str(datetime.now()) + ": App crashed in func. finviz_calls while processing command with exception: " + traceback.format_exc())
	return page_source
		
def get_stock_name(page_source):
		start = page_source.index("quote.ashx?t=") + len("quote.ashx?t=")
		end = page_source.index("&ty=c&p=d&b=1", start )
		stk = page_source[start:end]
		sector = ""
		if len(banned_sectors) > 0:
			start = 0
			for i in range(0,5):
				start = page_source.index(stk + "&ty=c&p=d&b=1", start) + len(stk) + len('&ty=c&p=d&b=1" class="">') + 13
			end = page_source.index('</a></td><td height="', start)
			sector = page_source[start:end]
		return stk, page_source[start:end]

def check_buy_opportunity(stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	weeks_perf = None
	todays_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','day','regular')", stk)
	weeks_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','week','regular')", stk)
	buy_permit = False

	if todays_perf != None and weeks_perf != None:
		todays_perf_size = 0
		avg_growth = 0.0
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
	else:
		print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	return buy_permit

def check_sell_opportunity(stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	weeks_perf = None
	todays_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','day','regular')", stk)
	weeks_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','week','regular')", stk)
	sale_permit = False

	if todays_perf != None and weeks_perf != None:
		avg_growth = 0.0
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
	else:
		print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	return sale_permit
	
def replace_parameter(old_param, new_param, url):
	init_url = url
	repl = re.subn(old_param, new_param, url)
	url = repl[0]
	replace_count = repl[1]
	return url, init_url, replace_count

def append_parameter(new_param, url):
	if new_param[:-3] not in url:
		start = url.index(',') + 1
		url = url[:start] + new_param + "," + url[start:]
	return url

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
	fromaddr = user_ids[2]
	toaddr = user_ids[2]
	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddr
	msg['Subject'] = "Stock Activity"

	msg.attach(MIMEText(message, 'plain'))

	try:
		server = smtplib.SMTP('smtp.gmail.com', 587)
		server.starttls()
		server.login(fromaddr, user_ids[3])
		text = msg.as_string()
		server.sendmail(fromaddr, toaddr, text)
		server.quit()
	except smtplib.SMTPAuthenticationError, e:
		print (str(datetime.now()) + " SMTPAuthenticationError: " + str(e))
	
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
				last_stock_present_price = float(robinhood_calls("last_trade_price('" + last_stock[j] + "')", last_stock[j]))
				if last_stock_present_price != None and last_stock_present_price > 0.0:
					new_balance = new_balance + last_stock_quantity[j] * last_stock_present_price
					gains_since_stk_purchase = 100.0*(last_stock_present_price - last_stock_purchase_price[j])/last_stock_purchase_price[j]
					print (str(datetime.now()) + ": Stock holding: " + last_stock[j] + " purchased on " + str(last_purchase_time[j]) + ", Gain since last purchase: " + str(gains_since_stk_purchase) + "%")
				elif last_stock_present_price == None:
					print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])

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
	if (day in range(1,6)) and (hour in range(9,14)):#mon-fri 910am-3pm, run every 5 minutes
		tts = 300
	elif (day in range(1,6)) and (hour > 14):#mon-fri 3pm-12am, sleep till 910 am
		tts = (33 - hour)*3600 - minute*60 - second + 600
	elif (day in range(1,6)) and (hour < 9):#mon-fri pre-8am, sleep till 910 am
		tts = (9-hour)*3600 - minute*60 - second + 600
	elif (day > 5):#weekend, sleep till monday 910am
		tts = (7-day)*24*3600 + (33-hour)*3600 - minute*60 - second + 600
	if tts > 300:
		_, _, _, _, _, _ = last_state_reader()
		d = datetime(1,1,1) + timedelta(seconds=tts)
		#print("Sleeping for ")
		#print("%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second))
		d = datetime.now() + timedelta(seconds=tts)
		#print("Wake up at " + d.strftime("%A"))
		#print("%d:%d:%d" % (d.hour, d.minute, d.second))
	return tts

def purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, final_stock):
	global max_stx_to_hold, my_trader, new_stocks_found

	final_stock_price = 0.0
	final_stock_price = float(robinhood_calls("last_trade_price('" + final_stock + "')", final_stock))

	if final_stock_price != None and final_stock_price > 0.0 and math.floor(free_cash/final_stock_price) > 0:
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
	elif final_stock_price == None:
		print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
			
def sale_accounting(stk, count, purchase_price, free_cash, stk_idx):
	sale_price = 0.0
	sale_price = float(robinhood_calls("last_trade_price('" + stk[stk_idx] + "')", stk[stk_idx]))

	if sale_price != None and sale_price > 0.0:
		free_cash = free_cash + float(count) * sale_price
		sale_logger(free_cash, stk_idx, len(stk))

		sale_gain = 100.0*(sale_price-purchase_price)/purchase_price
		print (str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		with open('daily_activity_log.txt', 'a`') as f:
			f.writelines(str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain) + '\n')
		send_email(str(datetime.now()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		print (str(datetime.now()) + " Free cash left: " + str(free_cash))

	elif sale_price == None:
		print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])

def result_check(url,last_stock,free_cash):
	global my_trader, new_stocks_found
	page_source = ""
	
	page_source = finviz_calls(url)

	if page_source != None:	
		stock = []
		prefix ="quote.ashx?t="

		for i in range (0,int(page_source.count(prefix)/11)):

			stk, sector = get_stock_name(page_source)
			for i in range(0,11):
				page_source = page_source.replace(str("quote.ashx?t=" + stk + "&ty=c&p=d&b=1"),"")#Delete first stock from page source string to arrive at next stock

			final_stock_price = float(robinhood_calls("last_trade_price('" + stk + "')", stk))
			if final_stock_price != None and final_stock_price <= free_cash:#Proceed only if stock price lower than available cash
				if stk not in new_stocks_found:
					json_obj = robinhood_calls("instruments('" + stk + "')", stk)

					if json_obj != None:
						stxx = [item for item in json_obj
								if item['symbol'] == stk]
						if stxx != []:
							stk_tradeable_on_robinhood = str(stxx[0]['tradeable'])			
						else:
							stk_tradeable_on_robinhood = "False"			
						if stk_tradeable_on_robinhood == "True" and stk not in last_stock:#Proceed only if stock tradeable on robinhood
							stock.append(stk)
					elif json_obj == None:
						print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])

				elif stk not in last_stock:
					stock.append(stk)
			elif final_stock_price == None:
				print str(datetime.now()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	elif page_source == None: 
		print str(datetime.now()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])

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
	
	page_source = finviz_calls("http://finviz.com/quote.ashx?t=" + stk + "&ty=c&p=d&b=1")
	if page_source != None:
		RSI = get_param_val('RSI (14)</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		Recom = get_param_val('">Recom</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
		if Recom > 2.8 or RSI > 65:
			SMA20 = get_param_val('">SMA20</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
			SMA50 = get_param_val('">SMA50</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
			Perf_week = get_param_val('">Perf Week</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
			Perf_month = get_param_val('">Perf Month</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source)
			if SMA20 > stk_grwth_purchase_threshold[0] or SMA50 > stk_grwth_purchase_threshold[0] or Perf_week > stk_grwth_purchase_threshold[0] or Perf_month > stk_grwth_purchase_threshold[0]: 
				sale_flag = True
	elif page_source == None: 
		print str(datetime.now()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])

	return sale_flag

def rearrange_stox(stk_array):
	sma_array = []
	page_source = ""
	stk_array = set(stk_array)
	for stk in stk_array:

		page_source = finviz_calls("http://finviz.com/quote.ashx?t=" + stk + "&ty=c&p=d&b=1")
		if page_source != None:
			sma_array.append(get_param_val('">SMA20</td><td width="8%" class="snapshot-td2" align="left"><b>', '</b></td>', page_source))
		elif page_source == None: 
			print str(datetime.now()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])

	return [x for (y,x) in sorted(zip(sma_array,stk_array))]

def optimize(last_stock,last_purchase_time,free_cash):
	global max_stx_to_hold
	#!!!!!!!!!!!!!test url below
	#init_url = []
	#init_url.append("http://finviz.com/screener.ashx?v=111&f=an_recom_holdbetter,fa_debteq_u1,fa_epsqoq_high,fa_netmargin_o5,fa_quickratio_o1,fa_roe_pos,ta_perf_1wdown,ta_perf2_4wdown,ta_rsi_os40,ta_sma20_pb,ta_sma200_pb,ta_sma50_pb&ft=4&ar=180")
	fin_stock = []
	for i in range(0,len(init_url)):
		url = init_url[i]
		prev_url = url
		fin_url = url
		repl_count = 0	
		tmp_stock = []
		select_order_index = 0
		tmp_stock = result_check(url,last_stock,free_cash)
		extra_param_rows = 0

		while extra_param_rows < len(extra_filters):#Add filters for PEG ratio/PE ratio, EPS Growth, Sales Growth if possible
			extra_param_columns = 0
			while len(tmp_stock) > 1 and extra_param_columns < len(extra_filters[extra_param_rows]):
					tmp_url = append_parameter(extra_filters[extra_param_rows][extra_param_columns], url)
					tmp_stock = result_check(tmp_url,last_stock,free_cash)
					if len(tmp_stock) > 0:
						fin_url = tmp_url
					extra_param_columns = extra_param_columns + 1
			url = fin_url
			tmp_stock = result_check(url,last_stock,free_cash)
			extra_param_rows = extra_param_rows + 1

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
			#if filter_success_flag == True and repl_count == 1:
				#print ("Filtered on " + select_order[select_order_index][2])
			select_order_index = select_order_index + 1

		fin_stock.extend(tmp_stock)
	if len(fin_stock) > 1:
		fin_stock = [rearrange_stox(fin_stock)[0]]#Arrange final list of stocks in order of highest SMA20 drop
	return fin_stock

if __name__ == '__main__':
	print ("Starting Loop..")
	last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader() 
	new_stocks_start_time = datetime.now()
	while True:
		start_time = datetime.now()
		if (datetime.now().isoweekday() in range(1,6)) and datetime.now().time() > datetime.strptime('9:09','%H:%M').time() and datetime.now().time() < datetime.strptime('15:01','%H:%M').time():

			for i in range(0,len(last_stock)):#Check if any stocks ready for sale
				if i < len(last_stock):
					if datetime.now().date() != last_purchase_time[i].date() and check_stk_sale(last_stock[i]):
						if check_sell_opportunity(last_stock[i]):
							sale_accounting(last_stock, last_stock_quantity[i], last_stock_purchase_price[i], free_cash, i)
							last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader()

			final_stock = optimize(last_stock,last_purchase_time, free_cash)#Retreive latest batch of buy-able stocks

			for i in range(0,len(final_stock)):#Check if any stocks ready for purchase
				if final_stock[i] not in new_stocks_found:
					print(str(datetime.now()) + ": New stock found: " + str(final_stock[i]))
					new_stocks_found.append(final_stock[i])
				if check_buy_opportunity(final_stock[i]):
					purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, final_stock[i])
					last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance = last_state_reader()

		if (datetime.now() - new_stocks_start_time).days > 30.0:#Refresh new_stocks_found array every 30 days to remove stale stocks
			new_stocks_found = []
			new_stocks_start_time = datetime.now()

		sleep_duration = time_to_sleep()
		compute_time = (datetime.now() - start_time).seconds + (datetime.now() - start_time).microseconds/1000000.0
		time.sleep(sleep_duration-compute_time)
		if sleep_duration > 300:
			print datetime.now().date()