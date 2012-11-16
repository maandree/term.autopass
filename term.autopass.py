#!/usr/bin/env python3
# -*- mode: python, coding: utf-8 -*-

'''
term.autopass – pty providing password manager capability

Copyright © 2012  Mattias Andrée (maandree@kth.se)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys
import pty
import time
import signal
from subprocess import Popen, PIPE
from threading import Thread, Lock



READ_BUF = 4096
MASTER_STTY_SLEEP = 0.200
SLAVE_STTY_SLEEP = 0.100
DEBUG_MODE = True



'''
Hack to enforce UTF-8 in output (in the future, if you see anypony not using utf-8 in
programs by default, report them to Princess Celestia so she can banish them to the moon)

@param  text:str  The text to print (empty string is default)
@param  end:str   The appendix to the text to print (line breaking is default)
'''
def print(text = '', end = '\n'):
    sys.stdout.buffer.write((str(text) + end).encode('utf-8'))
    sys.stdout.buffer.flush()



class TermAutopass:
    def __init__(self):
        self.inhertiedStty = Popen(['stty', '-g'], stdin=sys.stdout, stdout=PIPE, stderr=PIPE).communicate()[0][:-1]
        Popen(['stty', '-icanon', '-echo', '-isig', '-ixoff', '-ixon'], stdin=sys.stdout).wait()
        try:
            termsize = (24, 80)
            for channel in (sys.stderr, sys.stdout, sys.stdin):
                termsize = Popen(['stty', 'size'], stdin=channel, stdout=PIPE, stderr=PIPE).communicate()[0]
                if len(termsize) > 0:
                    termsize = termsize.decode('utf8', 'replace')[:-1].split(' ') # [:-1] removes a \n
                    termsize = [int(item) for item in termsize]
                    break
            (self.termh, self.termw) = termsize
            
            (self.master, self.slave) = pty.openpty()
            self.master_write = os.fdopen(self.master, 'wb')
            self.master_read  = os.fdopen(self.master, 'rb', 0)
            self.slave        = os.fdopen(self.slave,  'wb')
            self.stdin        = os.fdopen(0, 'rb', 0)
            
            slave_thread = SlaveThread(self)
            slave_thread.daemon = True
            slave_thread.start()
            
            master_thread = MasterThread(self)
            master_thread.daemon = True
            master_thread.start()
            
            master_stty_thread = MasterSTTYThread(self)
            master_stty_thread.daemon = True
            master_stty_thread.start()
            
            slave_stty_thread = SlaveSTTYThread(self)
            slave_stty_thread.daemon = True
            slave_stty_thread.start()
            
            Popen(['stty', self.inhertiedStty, 'rows',  str(self.termh), 'columns', str(self.termw)], stdin=self.master_write).wait()
            proc = Popen([os.getenv('SHELL', 'sh')], stdin=self.slave, stdout=self.slave, stderr=self.slave)
            proc.wait()
            
            self.master_write.close()
            self.slave.close()
            self.stdin.close()
        
        finally:
            Popen(['stty', self.inhertiedStty], stdin=sys.stdout).wait()



class MasterSTTYThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(MasterSTTYThread)')
        else:
            try:
                self.implementation();
            except:
                pass
    
    def implementation(self):
        master_write = self.term.master_write
        master_read = self.term.master_read
        stdin = self.term.stdin
        last = str(self.term.termh) + ' ' + str(self.term.termw) + '\n'
        while not (stdin.closed or master_write.closed or master_read.closed):
            stty = Popen(['stty', 'size'], stdin=sys.stdout, stdout=PIPE, stderr=PIPE).communicate()[0].decode('utf8', 'replace')
            if stty != last:
                last = stty
                (self.term.termh, self.term.termw) = [int(item) for item in stty[:-1].split(' ')]
                Popen(['stty', 'rows',  str(self.term.termh), 'columns', str(self.term.termw)], stdin=self.term.master_write).wait()
            time.sleep(MASTER_STTY_SLEEP)


class SlaveSTTYThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(SlaveSTTYThread)')
        else:
            try:
                self.implementation();
            except:
                pass
    
    def implementation(self):
        master_write = self.term.master_write
        master_read = self.term.master_read
        stdin = self.term.stdin
        last = ''
        while not (stdin.closed or master_write.closed or master_read.closed):
            stty = Popen(['stty', '-g'], stdin=master_write, stdout=PIPE, stderr=PIPE).communicate()[0].decode('utf8', 'replace')
            if stty != last:
                last = stty
                Popen(['stty', stty[:-1]], stdin=stdin, stdout=PIPE, stderr=PIPE).wait()
                Popen(['stty', '-icanon', '-echo', '-isig', '-ixoff', '-ixon'], stdin=stdin).wait()
            time.sleep(SLAVE_STTY_SLEEP)


class MasterThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(MasterThread)')
        else:
            try:
                self.implementation();
            except:
                pass
    
    def implementation(self):
        master_write = self.term.master_write
        master_read = self.term.master_read
        stdin = self.term.stdin
        while not (stdin.closed or master_write.closed or master_read.closed):
            b = stdin.read(READ_BUF)
            if b is None:
                continue
            master_write.write(b)
            master_write.flush()


class SlaveThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(SlaveThread)')
        else:
            try:
                self.implementation();
            except:
                pass
    
    def implementation(self):
        master_write = self.term.master_write
        master_read = self.term.master_read
        stdin = self.term.stdin
        while not (stdin.closed or master_write.closed or master_read.closed):
            b = master_read.read(READ_BUF)
            if b is None:
                continue
            sys.stdout.buffer.write(b)
            sys.stdout.buffer.flush()


'''
Start if mane script
'''
if __name__ == '__main__':
    TermAutopass()

