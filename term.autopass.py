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
import signal
from subprocess import Popen, PIPE
from threading import Thread, Lock



READ_BUF = 4096
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
        self.openterminals = 0
        
        Popen(['stty', '-icanon', '-echo', '-isig', '-ixoff', '-ixon'], stdin=sys.stdout).wait()
        
        try:
            termsize = (24, 80)
            for channel in (sys.stderr, sys.stdout, sys.stdin):
                termsize = Popen(['stty', 'size'], stdin=channel, stdout=PIPE, stderr=PIPE).communicate()[0]
                if len(termsize) > 0:
                    termsize = termsize.decode('utf8', 'replace')[:-1].split(' ') # [:-1] removes a \n
                    termsize = [int(item) for item in termsize]
                    break
            (termh, termw) = termsize
            
            (self.master, self.slave) = pty.openpty()
            self.master_write = os.fdopen(self.master, 'wb')
            self.master_read  = os.fdopen(self.master, 'rb', 0)
            self.slave        = os.fdopen(self.slave,  'wb')
            self.stdin        = os.fdopen(0, 'rb', 0)
            
            read_thread = ReadThread(self)
            read_thread.daemon = True
            read_thread.start()
            
            write_thread = WriteThread(self)
            write_thread.daemon = True
            write_thread.start()
            
            sttyFlags = ['icanon', 'brkint', 'imaxbel', 'eol', '255', 'eol2', '255', 'swtch', '255', 'ixany', 'iutf8']
            Popen(['stty', 'rows',  str(termh), 'columns', str(termw)] + sttyFlags, stdin=self.master_write).wait()
            proc = Popen([os.getenv('SHELL', 'sh')], stdin=self.slave, stdout=self.slave, stderr=self.slave)
            proc.wait()
            
            self.master_write.close()
            self.slave.close()
            self.stdin.close()
        
        finally:
            Popen(['stty', 'icanon', 'echo', 'isig', 'ixoff', 'ixon'], stdin=sys.stdout).wait()


class WriteThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(w)')
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


class ReadThread(Thread):
    def __init__(self, term):
        Thread.__init__(self)
        self.term = term
    
    def run(self):
        if DEBUG_MODE:
            self.implementation();
            print('(r)')
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

