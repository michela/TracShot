#!/usr/bin/env python
# encoding: utf-8
"""
sms.py

Created by Michela Ledwidge on 2007-10-05.
Copyright (c) 2007 MOD Films. All rights reserved.

./var/lib/python-support/python2.4/trac/ticket/web_ui.py
"""

import sys
import os
import MySQLdb
import StringIO
import urllib
import urllib2
import re

from trac.core import *
from trac.ticket.api import ITicketChangeListener
from trac.ticket.notification import TicketNotifyEmail
	
class TicketNotifySMS(Component):
	implements(ITicketChangeListener)
	
	smsAccount = 'user'
	smsPassword = 'password'     # cripple to prevent SMS being sent
	smsFrom = 'MOD Films'

	# TODO - alerts for creation and deletion
	def ticket_created(self, ticket):
		self.env.log.debug("ticket_created - TicketNotifySMS")
		# Q) why does debug work on DEBUG setting but not INFO?
		msg = "New render #%s (%s) uploaded" % (ticket.id, ticket.values['summary'])
		tne = TicketNotifyEmail(self.env)
		peeps = tne.get_recipients(ticket.id)
		list = {}
		for person in peeps:
			for p in person:
				list[p] = 1
		for k in list.keys():
			self.env.log.debug("recepient: %s" % k)
			if k != None:
				self.sms(k, str(ticket.time_changed), ticket.values['summary'], msg)
	
	def ticket_deleted(self, ticket):pass
	
	def ticket_changed(self,ticket,comment,author,old_values):
		self.env.log.debug("ticket_change - TicketNotifySMS: %s" % author)
		# Q) why does debug work on DEBUG setting but not INFO?
		db = self.env.get_db_cnx()
		cursor = db.cursor()
		sql = "select field, newvalue from ticket_change where ticket = %s ORDER BY time DESC LIMIT 1" % ticket.id
		cursor.execute(sql)
		data = cursor.fetchall()
		msg = ''
		for row in data:
			# TODO check alerts aren't needed on other fields
			if row[0] == 'comment':
				patt = re.compile('{{{(.+)}}}')
				mobj = patt.match(row[1])
				self.env.log.debug('comment value: ' + row[1])
				body = ''
				try:
					body = mobj.group(0)
				except AttributeError:
					self.env.log.debug('no brackets')
					body = row[1]
				msg = "Re: shot %s - %s" % (ticket.values['summary'], body )
				# ticket.id if necessary
		tne = TicketNotifyEmail(self.env)
		peeps = tne.get_recipients(ticket.id)
		list = {}
		for person in peeps:
			for p in person:
				list[p] = 1
		for k in list.keys():
			self.env.log.debug("recepient: %s" % k)
			if k != None:
				self.sms(k, str(ticket.time_changed), ticket.values['summary'], msg)

	def lookup_number(self, username):
		numbers = []
		result = ','		
		db = self.env.get_db_cnx()
		cursor = db.cursor()
		count = 0
		sql = "SELECT mobile FROM user_sms WHERE username = '" + username + "' AND active = 1"
		self.env.log.debug(sql)
		try:
			cursor.execute(sql)
			data = cursor.fetchall()
			self.env.log.debug(data)
			for row in data:
				count += 1
				numbers.append(row[0])
			if count == 0:
				self.env.log.debug("No alerts to be sent: " + int(cursor.rowcount) + ' ' + data)
		except:
			self.env.log.debug("DB error: Was unable to read from table")
			# TODO- above mesg is misleading - find out what exception is when no results back - separate out error
			# Close db connection
		cursor.close()
		return result.join(numbers)

	def send_sms(self, numbers, msg):
		if numbers != '':
			url = "https://www.intellisoftware.co.uk/smsgateway/sendmsg.aspx"
			values = {'username' : self.smsAccount,
			          'password' : self.smsPassword,
			          'to' : numbers,
			          'from': self.smsFrom, 
			          'text': msg}
			data = urllib.urlencode(values)
			self.env.log.debug(url + '?' + data)
			req = urllib2.Request(url, data)
			response = urllib2.urlopen(req)
			the_page = response.read()
			if the_page[:3] == 'ERR':
				self.env.log.debug('SMS not sent: ' + the_page)
			else:
				# log to sms log
				self.env.log.debug('SMS sent: ' + the_page)
			return the_page

	def sms(self, username, timestamp, shot, msg):
		"lookup number by username and if SMS alert feature activated, send an alert"

		number = str(self.lookup_number(username))
		#msg = "New render of %s uploaded by %s (%s)" % (shot, username, timestamp)
		print "number: " + number
		#print msg
		response = self.send_sms( number[1:], msg )


	
