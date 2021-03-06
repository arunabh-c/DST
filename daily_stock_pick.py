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
import numpy
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import datetime, timedelta
from Robinhood import Robinhood

start_seed = 1000.0
max_stx_to_hold = 5
stk_grwth_purchase_threshold = [0.09,1.0]#in %
expired_stk_grwth_purchase_threshold = 0.0
total_5minute_intervals_to_check_avg_growth = 10
scrap_stk_threshold = 50.0
new_stocks_found = []
reset_color = "\033[0m"
my_trader = None

with open('select_order.csv', 'rb') as f:
	reader = csv.reader(f)
	select_order = list(reader)

with open('extra_filters.csv', 'rb') as f:
	reader = csv.reader(f)
	extra_filters = list(reader)

with open('banned_sectors.csv') as f:
	banned_sectors = f.readlines()
	banned_sectors = [x.strip() for x in banned_sectors]

with open('urls.txt') as f:
	init_url = f.readlines()
	init_url = [x.strip() for x in init_url]

with open('user_details.txt') as f:
	user_ids = f.readlines()
	user_ids = [x.strip() for x in user_ids]

def init_robinhood():
	global my_trader
	my_trader = Robinhood()
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
			print (str(datetime.utcnow()) + ' ***ROBINHOOD CALL EXCEPTION***: ' + stk + ", " + command + ", " + traceback.format_exc() + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
			if try_counter == 10:
				send_email(str(datetime.utcnow()) + ": App crashed in func. robinhood calls while processing command: " + command + " for stock " + stk + " with error: " + traceback.format_exc())
	return value_to_return
		
def finviz_calls(url):
	exec_flag = False
	page_source = None
	try_counter = 0
	while exec_flag == False and try_counter < 10:
		try:
			req = urllib2.Request(url, headers={'User-Agent' : "Magic Browser"}) 
			response = urllib2.urlopen(req)
			page_source = response.read()
			exec_flag = True
		except Exception:
			import traceback
			print (str(datetime.utcnow()) + ' ***FINVIZ CALL EXCEPTION***: ' + traceback.format_exc() + ": Waiting for 10 seconds before re-attempting..")
			try_counter = try_counter + 1
			time.sleep(10)
			if try_counter == 10:
				send_email(str(datetime.utcnow()) + ": App crashed in func. finviz_calls while processing command with exception: " + traceback.format_exc())
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

def get_avg_growth(historicals, todays_perf_size):
	global total_5minute_intervals_to_check_avg_growth
	avg_growth = 0.0
	for i in range(0,total_5minute_intervals_to_check_avg_growth):
		avg_growth = avg_growth + 10.0*(float(historicals[todays_perf_size-1-i]['close_price']) - float(historicals[todays_perf_size-2-i]['close_price']))/(float(historicals[todays_perf_size-2-i]['close_price']))
	return avg_growth

def check_buy_opportunity(stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	weeks_perf = None
	todays_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','day','regular')", stk)
	weeks_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','week','regular')", stk)
	buy_permit = False

	if todays_perf != None and weeks_perf != None:
		todays_perf_size = 0
		todays_perf_size = len(todays_perf['historicals'])
		weeks_perf_size = len(weeks_perf['historicals'])
		if todays_perf_size > 0:
			last_date_stamp = datetime.strptime(todays_perf['historicals'][todays_perf_size-1]['begins_at'], '%Y-%m-%dT%H:%M:%SZ').date()
			if todays_perf_size > 11 and last_date_stamp == datetime.utcnow().date():#Avg. % growth of last 50 minutes
				close_price_right_now = float(todays_perf['historicals'][todays_perf_size-1]['close_price'])
				yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-1]['close_price'])
				day_before_yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-79]['close_price'])
				day_before_day_before_yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-157]['close_price'])
				perf_today = 100.0 * (close_price_right_now - yesterday_close_price)/yesterday_close_price
				perf_yesterday = 100.0 * (yesterday_close_price - day_before_yesterday_close_price)/day_before_yesterday_close_price
				perf_day_before_yesterday = 100.0 * (day_before_yesterday_close_price - day_before_day_before_yesterday_close_price)/day_before_day_before_yesterday_close_price
				avg_growth = get_avg_growth(todays_perf['historicals'], todays_perf_size)
				if  (perf_today <= stk_grwth_purchase_threshold[0] or perf_yesterday <= stk_grwth_purchase_threshold[0]) and (perf_yesterday <= stk_grwth_purchase_threshold[0] or perf_day_before_yesterday <= stk_grwth_purchase_threshold[0]) and (avg_growth >= stk_grwth_purchase_threshold[0] and avg_growth <= stk_grwth_purchase_threshold[1]):
					print (str(datetime.utcnow()) + " Stock ready to be purchased: " + stk)
					print (str(datetime.utcnow()) + " Performance today for " + stk + ": " + str(perf_today))
					print (str(datetime.utcnow()) + " Performance yesterday for " + stk + ": " + str(perf_yesterday))
					print (str(datetime.utcnow()) + " Performance day before yesterday for " + stk + ": " + str(perf_day_before_yesterday))
					print (str(datetime.utcnow()) + " Last " + str(5*total_5minute_intervals_to_check_avg_growth) + " minutes growth for " + stk + ": " + str(avg_growth))

					buy_permit = True
	else:
		print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	return buy_permit

def test_short_term_sale(todays_perf, weeks_perf, stk):
	global stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth

	todays_perf_size = len(todays_perf['historicals'])
	weeks_perf_size = len(weeks_perf['historicals'])
	if todays_perf_size > 0:
		last_date_stamp = datetime.strptime(todays_perf['historicals'][todays_perf_size-1]['begins_at'], '%Y-%m-%dT%H:%M:%SZ').date()

		if todays_perf_size > 11 and last_date_stamp == datetime.utcnow().date():#Avg. % growth of last 50 minutes
			close_price_right_now = float(todays_perf['historicals'][todays_perf_size-1]['close_price'])
			yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-1]['close_price'])
			day_before_yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-79]['close_price'])
			day_before_day_before_yesterday_close_price = float(weeks_perf['historicals'][weeks_perf_size-todays_perf_size-157]['close_price'])
			perf_today = 100.0 * (close_price_right_now - yesterday_close_price)/yesterday_close_price
			perf_yesterday = 100.0 * (yesterday_close_price - day_before_yesterday_close_price)/day_before_yesterday_close_price
			perf_day_before_yesterday = 100.0 * (day_before_yesterday_close_price - day_before_day_before_yesterday_close_price)/day_before_day_before_yesterday_close_price
			avg_growth = get_avg_growth(todays_perf['historicals'], todays_perf_size)
			#if stk performance (today or yesterday) and(yesterday or day before) was in range and avg growth for last n 5-minute intervals in negative range sell
			if (perf_today >= stk_grwth_purchase_threshold[0] or perf_yesterday >= stk_grwth_purchase_threshold[0]) and (perf_day_before_yesterday >= stk_grwth_purchase_threshold[0] or perf_yesterday >= stk_grwth_purchase_threshold[0]) and (avg_growth <= -stk_grwth_purchase_threshold[0] and avg_growth >= -stk_grwth_purchase_threshold[1]):
				print (str(datetime.utcnow()) + " Stock ready to be sold: " + stk)
				print (str(datetime.utcnow()) + " Performance today for " + stk + ": " + str(perf_today))
				print (str(datetime.utcnow()) + " Performance yesterday for " + stk + ": " + str(perf_yesterday))
				print (str(datetime.utcnow()) + " Performance day before yesterday for " + stk + ": " + str(perf_day_before_yesterday))
				print (str(datetime.utcnow()) + " Last " + str(5*total_5minute_intervals_to_check_avg_growth) + " minutes growth for " + stk + ": " + str(avg_growth))
				return True
	return False

def check_sell_opportunity(stk):
	todays_perf = None
	weeks_perf = None
	todays_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','day','regular')", stk)
	weeks_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','week','regular')", stk)
	sale_permit = False

	if todays_perf != None and weeks_perf != None:
		sale_permit = test_short_term_sale(todays_perf, weeks_perf, stk)
	else:
		print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	return sale_permit

def check_expired_sell_opportunity(stk):
	global expired_stk_grwth_purchase_threshold, total_5minute_intervals_to_check_avg_growth
	todays_perf = None
	todays_perf = robinhood_calls("get_historical_quotes('" + stk + "','5minute','day','regular')", stk)
	
	if todays_perf != None:
		todays_perf_size = len(todays_perf['historicals'])
		if todays_perf_size > 11:
			last_date_stamp = datetime.strptime(todays_perf['historicals'][todays_perf_size-1]['begins_at'], '%Y-%m-%dT%H:%M:%SZ').date()
			if last_date_stamp == datetime.utcnow().date():
				avg_growth = get_avg_growth(todays_perf['historicals'], todays_perf_size)
				if (avg_growth <= expired_stk_grwth_purchase_threshold):
					print (str(datetime.utcnow()) + " Expired Stock ready to be sold: " + stk)
					print (str(datetime.utcnow()) + " Last " + str(5*total_5minute_intervals_to_check_avg_growth) + " minutes growth for " + stk + ": " + str(avg_growth))
					return True
	return False
	
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

def purchase_logger(stock, quantity, stock_price, free_cash):#Log latest stocks information into state file post purchase
	
	file_write_array = [str(datetime.utcnow().strftime("%Y-%m-%d %H:%M")),stock, str(quantity), str(stock_price), str(free_cash)]
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
	except Exception:
		import traceback
		print (str(datetime.utcnow()) + ' ***EMAIL EXCEPTION***: ' + traceback.format_exc())
	
def last_state_reader():
		global start_seed, my_trader, max_stx_to_hold
		holdings_array = [[], [], [], []]
		last_purchase_time = []
		last_stock = []
		last_stock_quantity = []
		last_stock_purchase_price = []
		re_purchasable = []
		scrap_stox = 0
		f = open('daily_last_state.txt', 'r')		
		try:
			row_counter = 0
			for line in f:
				if ((row_counter < 4) and line != '\n'):
					line = line.decode('unicode_escape').encode('ascii','ignore')
					holdings_array[row_counter] = (line.rstrip('\n')).split(",")
					if holdings_array[row_counter][0] == '':
						holdings_array[row_counter].pop(0)
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
				re_purchasable.append(0.0)
				last_stock_present_price = 0.0
				stock_quote = robinhood_calls("last_trade_price('" + last_stock[j] + "')", last_stock[j])
				if stock_quote != None:
					last_stock_present_price = float(stock_quote[0][0])
					if last_stock_present_price != None and last_stock_present_price > 0.0:
						stk_value = last_stock_quantity[j] * last_stock_present_price
						new_balance = new_balance + stk_value
						gains_since_stk_purchase = 100.0*(last_stock_present_price - last_stock_purchase_price[j])/last_stock_purchase_price[j]
						if gains_since_stk_purchase >= 0.0:
							prefix_color = "\033[1;32;40m "
						else:
							prefix_color = "\033[1;31;40m "
						print (str(datetime.utcnow()) + ": Stock holding: " + last_stock[j] + " purchased on " + str(last_purchase_time[j]) + ", Gain since last purchase:" + prefix_color + str(gains_since_stk_purchase) + "%" + reset_color)
						if stk_value < scrap_stk_threshold:
							scrap_stox += 1
							re_purchasable[j] = 1.0
				else:
					print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
			avail_cash = free_cash / max (max_stx_to_hold - len(holdings_array[0]) + scrap_stox,  1)

			gains_since_beginning = 100.0*(new_balance - start_seed)/start_seed
			if gains_since_beginning >= 0.0:
				prefix_color = "\033[1;32;40m "
			else:
				prefix_color = "\033[1;31;40m "
			print (str(datetime.utcnow()) + " Net Gain since beginning:" + prefix_color + str(gains_since_beginning) + "%" + reset_color)
			print (str(datetime.utcnow()) + " Free Cash: " + str(free_cash))
			print (str(datetime.utcnow()) + " Latest Balance: " + str(new_balance))
		else:
			new_balance = start_seed
			free_cash = start_seed
			avail_cash = free_cash / max_stx_to_hold
		return last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance, avail_cash, re_purchasable

def time_to_sleep():
	day = datetime.utcnow().isoweekday()
	hour =  datetime.utcnow().hour
	minute = datetime.utcnow().minute
	second = datetime.utcnow().second
	tts = 300
	if (day in range(1,6)):
		if (hour in range(14,23)):
			tts = 300
		elif (hour > 22):#mon-fri 3pm-12am, sleep till 910 am
			tts = (38 - hour)*3600 - minute*60 - second + 600
		elif (hour < 14):#mon-fri pre-8am, sleep till 910 am
			tts = (14-hour)*3600 - minute*60 - second + 600
	elif (day > 5):#weekend, sleep till monday 910am
		tts = (7-day)*24*3600 + (38-hour)*3600 - minute*60 - second + 600
	if tts > 300:
		_, _, _, _, _, _, _, _ = last_state_reader()
		#d = datetime(1,1,1) + timedelta(seconds=tts)
		#print("Sleeping for ")
		#print("%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second))
		#d = datetime.utcnow() + timedelta(seconds=tts)
		#print("Wake up at " + d.strftime("%A"))
		#print("%d:%d:%d" % (d.hour, d.minute, d.second))
	return tts

def purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, avail_cash, final_stock):
	global my_trader, new_stocks_found

	final_stock_price = 0.0
	stock_quote = robinhood_calls("last_trade_price('" + final_stock + "')", final_stock)
	if stock_quote != None:
		final_stock_price = float(stock_quote[0][0])

	if final_stock_price > 0.0:
		total_stocks = math.floor(avail_cash/final_stock_price)
		if total_stocks > 0.0:
			final_purchase_amount = final_stock_price * total_stocks
			free_cash = free_cash - final_purchase_amount

			purchase_logger(final_stock, total_stocks, final_stock_price, free_cash)
			print (str(datetime.utcnow()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount))
			with open('daily_activity_log.txt', 'a`') as f:
				f.writelines(str(datetime.utcnow()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount) + '\n')
			send_email(str(datetime.utcnow()) + " Stock purchased: " + final_stock + ", Total stocks: " + str(total_stocks) + ", Final purchase amount: " + str(final_purchase_amount))
			print (str(datetime.utcnow()) + " Free cash left: " + str(free_cash))
			if final_stock in new_stocks_found:#Remove purchased stock from new_stocks_found
				new_stocks_found.remove(final_stock)
		else:
			print (str(datetime.utcnow()) + "Not enough cash left to buy " + final_stock)
	elif final_stock_price == None:
		print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
			
def check_stock_expiry_sale(stk, purchase_date, purchase_price):
	stock_quote = robinhood_calls("last_trade_price('" + stk + "')", stk)
	if stock_quote != None:
		current_price = float(stock_quote[0][0])
		gain = (current_price-purchase_price)/purchase_price
		number_of_days = abs((datetime.utcnow() - purchase_date).days)
		if ((number_of_days > 45) or (number_of_days > 30 and gain >= 0.0) or (number_of_days > 12 and gain >= 0.1)):
			return True
	return False

def sale_accounting(stk, count, purchase_price, free_cash, stk_idx):
	sale_price = 0.0
	stock_quote = robinhood_calls("last_trade_price('" + stk[stk_idx] + "')", stk[stk_idx])
	if stock_quote != None:
		sale_price = float(stock_quote[0][0])

	if sale_price > 0.0:
		free_cash = free_cash + float(count) * sale_price
		sale_logger(free_cash, stk_idx, len(stk))

		sale_gain = 100.0*(sale_price-purchase_price)/purchase_price
		print (str(datetime.utcnow()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		with open('daily_activity_log.txt', 'a') as f:
			f.writelines(str(datetime.utcnow()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain) + '\n')
		send_email(str(datetime.utcnow()) + " Stock sold: " + stk[stk_idx] + ", Profit % made: " + str(sale_gain))
		print (str(datetime.utcnow()) + " Free cash left: " + str(free_cash))

	elif sale_price == None:
		print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])

def result_check(url,last_stock,free_cash,re_purchase):
	global my_trader, new_stocks_found
	page_source = ""
	stock = []
	
	page_source = finviz_calls(url)

	if page_source != None:	
		prefix ="quote.ashx?t="

		for i in range (0,int(page_source.count(prefix)/11)):

			stk, sector = get_stock_name(page_source)
			for i in range(0,11):
				page_source = page_source.replace(str("quote.ashx?t=" + stk + "&ty=c&p=d&b=1"),"")#Delete first stock from page source string to arrive at next stock
			final_stock_price = 0.0
			stock_quote = robinhood_calls("last_trade_price('" + stk + "')", stk)
			if stock_quote != None:
				final_stock_price = float(stock_quote[0][0])
			if final_stock_price != 0.0 and final_stock_price <= free_cash:#Proceed only if stock price lower than available cash
				if stk not in new_stocks_found:
					json_obj = robinhood_calls("instruments('" + stk + "')", stk)

					if json_obj != None:
						stxx = [item for item in json_obj
								if item['symbol'] == stk]
						if stxx != []:
							stk_tradeable_on_robinhood = str(stxx[0]['tradeable'])			
						else:
							stk_tradeable_on_robinhood = "False"			
						if stk_tradeable_on_robinhood == "True" and (stk not in last_stock or re_purchase[last_stock.index(stk)] == 1.0):#Proceed only if stock tradeable on robinhood
							stock.append(stk)
					elif json_obj == None:
						print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])

				elif stk not in last_stock or re_purchase[last_stock.index(stk)] == 1.0:
					stock.append(stk)
			elif final_stock_price == None:
				print str(datetime.utcnow()) + " Robinhood Data retrieve failed @ " + str(inspect.stack()[0][3])
	elif page_source == None: 
		print str(datetime.utcnow()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])

	return stock

def get_param_val(param, end, page_source):#parame = keyword/start,end = end 
		start = page_source.index(param) + len(param)
		end = page_source.index(end, start)
		if page_source[start:end][0] == '<':#Accounts for color component
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
		print str(datetime.utcnow()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])

	return sale_flag

def rearrange_stox(stk_array):
	rank_array = numpy.zeros(len(stk_array))
	page_source = ""
	check_list = ['">SMA200</td><td width="8%" class="snapshot-td2" align="left"><b>', 'RSI (14)</td><td width="8%" class="snapshot-td2" align="left"><b>', 'PEG</td><td width="8%" class="snapshot-td2" align="left"><b>', 'P/E</td><td width="8%" class="snapshot-td2" align="left"><b>']
	if len(stk_array) > 1:
		for k in range (0, len(check_list)):#rank stks in stk_array by check_list items
			var_array = []#reset rank array 
			for stk in stk_array:#cycle through stocks given a check list item
				page_source = finviz_calls("http://finviz.com/quote.ashx?t=" + stk + "&ty=c&p=d&b=1")#retrieve entire stk stat page
				if page_source != None:
					var = get_param_val(check_list[k], '</b></td>', page_source)#retrieve checklist item for stock
					if var == None:
						var = 999999.9#assign high value for stocks with checklist item unknown to place them at end of ranking
					var_array.append(var)
				elif page_source == None: 
					print str(datetime.utcnow()) + " Finviz Data retrieve failed @ " + str(inspect.stack()[0][3])
			output = [0] * len(var_array)
			for i, x in enumerate(sorted(range(len(var_array)), key=lambda y: var_array[y])):
				output[x] = i#rank all stocks for check list items, arrange sorted rank in original order of stox
			rank_array = rank_array + output#cumulatively add ranks

	return [x for (y,x) in sorted(zip(rank_array,stk_array))]

def optimize(last_stock,last_purchase_time,free_cash,re_purchase):
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
		tmp_stock = result_check(url,last_stock,free_cash,re_purchase)
		extra_param_rows = 0

		while extra_param_rows < len(extra_filters):#Add filters for PEG ratio/PE ratio, EPS Growth, Sales Growth if possible
			extra_param_columns = 0
			while len(tmp_stock) > 1 and extra_param_columns < len(extra_filters[extra_param_rows]):
					tmp_url = append_parameter(extra_filters[extra_param_rows][extra_param_columns], url)
					tmp_stock = result_check(tmp_url,last_stock,free_cash,re_purchase)
					if len(tmp_stock) > 0:
						fin_url = tmp_url
					extra_param_columns = extra_param_columns + 1
			url = fin_url
			tmp_stock = result_check(url,last_stock,free_cash,re_purchase)
			extra_param_rows = extra_param_rows + 1

		while len(tmp_stock) > 1 and select_order_index < len(select_order):
			filter_success_flag = False
			if len(tmp_stock) > 1:
				url, prev_url, repl_count = replace_parameter(select_order[select_order_index][0],select_order[select_order_index][1], url)
				tmp_stock = result_check(url,last_stock,free_cash,re_purchase)
				filter_success_flag = True
			if tmp_stock == None or len(tmp_stock) < 1:
				url = prev_url
				tmp_stock = result_check(url,last_stock,free_cash,re_purchase)
				filter_success_flag = False
			'''if filter_success_flag == True and repl_count == 1:#Debug Only Line, comment out for real run
				print ("Filtered on " + select_order[select_order_index][2])'''
			select_order_index = select_order_index + 1

		fin_stock.extend(tmp_stock)#concatenates tmp_stock to fin_stock
	if len(fin_stock) > 1:
		fin_stock = [rearrange_stox(set(fin_stock))[0]]#Arrange final list of stocks in order of highest SMA200 drop. set(fin_stock) ensures duplicates eliminated
	return fin_stock

if __name__ == '__main__':
	print ("Starting Loop..")
	init_robinhood()
	last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance, avail_cash, re_purchase = last_state_reader() 
	new_stocks_start_time = datetime.utcnow()
	while True:
		start_time = datetime.utcnow()
				
		#if True:
		if (datetime.utcnow().isoweekday() in range(1,6)) and datetime.utcnow().time() > datetime.strptime('14:09','%H:%M').time() and datetime.utcnow().time() < datetime.strptime('22:01','%H:%M').time():
			for i in range(0,len(last_stock)):#Check if any stocks ready for sale
				if i < len(last_stock):
					if datetime.utcnow().date() != last_purchase_time[i].date():
						if ((check_stk_sale(last_stock[i]) and check_sell_opportunity(last_stock[i])) or (check_stock_expiry_sale(last_stock[i],last_purchase_time[i],last_stock_purchase_price[i]) and check_expired_sell_opportunity(last_stock[i]))):
							sale_accounting(last_stock, last_stock_quantity[i], last_stock_purchase_price[i], free_cash, i)
							last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance, avail_cash, re_purchase = last_state_reader()
			final_stock = optimize(last_stock,last_purchase_time, avail_cash, re_purchase)#Retreive latest batch of buy-able stocks
			for i in range(0,len(final_stock)):#Check if any stocks ready for purchase
				if final_stock[i] not in new_stocks_found:
					print(str(datetime.utcnow()) + ": New stock found: " + str(final_stock[i]))
					new_stocks_found.append(final_stock[i])
				if check_buy_opportunity(final_stock[i]):
					purchase_accounting(last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, avail_cash, final_stock[i])
					last_purchase_time, last_stock, last_stock_quantity, last_stock_purchase_price, free_cash, new_balance, avail_cash, re_purchase = last_state_reader()

		if (datetime.utcnow() - new_stocks_start_time).days > 30.0:#Refresh new_stocks_found array every 30 days to remove stale stocks
			new_stocks_found = []
			new_stocks_start_time = datetime.utcnow()

		sleep_duration = time_to_sleep()
		compute_time = (datetime.utcnow() - start_time).seconds + (datetime.utcnow() - start_time).microseconds/1000000.0
		time.sleep(max(0.1,(sleep_duration-compute_time)))
		if sleep_duration > 300:
			init_robinhood()
			print datetime.utcnow().date()
