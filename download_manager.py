#!/usr/bin/env python
from urllib2 import Request,urlopen
from threading import Thread,Lock,current_thread,active_count
from time import sleep
from math import ceil
import os
import re

class Downloader:
    def __init__(self,url):
        self.FetchURL=url
        self.FileObj=None
        self.ThreadPoolNum=5
        self.SegmentLength=1024*1024*2
        self.FlagOfTerminated=False
        self.DictForDownloadingSegment={}
        self.ListForFinishedSegment=[]
        self.LockForSegment=Lock()
        self.LockForWrite=Lock()
        self.TotalByteOfDownloaded=0
        self.DictForRunningThread={}
        self.TotalIncomeBytes=0
        
    def FetchSegment(self,index,length):
#        print ('Sub-thread start running.....segment # '+str(index))
        ThreadID=str(current_thread())
        self.DictForRunningThread[ThreadID]=None
        TmpRequestHeader={'Range':'bytes='+\
                          str(index*self.SegmentLength)+\
                          '-'+\
                          str(index*self.SegmentLength+length)}
        while not self.FlagOfTerminated:
            try:
                Flag=self.LockForSegment.acquire(False)
                if not Flag:
#                    print ('Failed to hold segemnt lock try again ....segment # '+str(index))
                    sleep(1)
                    continue
                
                if str(index) in self.ListForFinishedSegment or index in self.DictForDownloadingSegment:
#                    print ('Nothing to do !!!!!!'+' segment # '+str(index))
                    return 0
                    
                self.DictForDownloadingSegment[str(index)]=None 
                self.LockForSegment.release()
                break
            except:
                pass
                
        if self.FlagOfTerminated:
            return 1
                
        try:
#            print ('INFO:Going to download segment # '+str(index)+'.....'+'segment #'+str(index))
            TmpRequestObj=Request(self.FetchURL,headers=TmpRequestHeader)
            TmpResponseObj=urlopen(TmpRequestObj,timeout=5)
            TmpResponseHeader=TmpResponseObj.info().dict
            TotalByteForCurrentSegment=int(min(self.SegmentLength,int(TmpResponseHeader['content-length'])))
            
            ByteObj=''
            while not self.FlagOfTerminated:
                if len(ByteObj)<TotalByteForCurrentSegment:
                    TmpByteObj=TmpResponseObj.read(1024)
                    ByteObj+=TmpByteObj
                    self.TotalIncomeBytes+=len(TmpByteObj)
                elif len(ByteObj)>=TotalByteForCurrentSegment:
                    break
            if self.FlagOfTerminated:
                return 1
            
        except Exception as e:
#            print ('Warning:Error occure while download segment # '+str(index))
#            print (e)
#            print ('Warning:Current thread is going to terminate ....'+' segment # '+str(index))
            self.DictForRunningThread.pop(ThreadID)
            self.DictForDownloadingSegment.pop(str(index))
            return 1
            
            
        try:
            while not self.FlagOfTerminated:
                Flag=self.LockForWrite.acquire(False)
                if not Flag:
                    sleep(1)
                    continue
                break
            if self.FlagOfTerminated:
                return 1
            
#            print ('Info:Going to write content to file segment # '+str(index))

            
            self.FileObj.seek(index*self.SegmentLength,0)
#            print ('Current position is '+str(self.FileObj.tell())+' segment # '+str(index))
            self.FileObj.write(ByteObj)
            self.FileObj.flush()
            os.fsync(self.FileObj.fileno())
            self.TotalByteOfDownloaded+=int(len(ByteObj))
#            print ('Downloaded bytes '+str(self.TotalByteOfDownloaded)+' segment # '+str(index))
            self.DictForDownloadingSegment.pop(str(index))
            self.ListForFinishedSegment.append(str(index))
            
#            print ('Info:Finished to write to file,segment # '+str(index))
#            print ('Begin index is '+str(index*self.SegmentLength)+'  and length is '+str(len(ByteObj))+'  segment # '+str(index))
#            print ('Finished segment list is '+str(self.ListForFinishedSegment)+' segment # '+str(index))
        except Exception as e:
#            print ('Warning:Error occure while writing to file # '+str(index))
            self.DictForDownloadingSegment.pop(str(index))
#            print (e)
        finally:
            self.LockForWrite.release()
            self.DictForRunningThread.pop(ThreadID)
        
#        print ('Current running thread '+str(self.DictForRunningThread)+' segment # '+str(index))
#        print ('Current Downloading segetment is '+str(self.DictForDownloadingSegment)+' segment # '+str(index))
            
    
    def Run(self):
        TmpRequestObj=Request(self.FetchURL)
        TmpResponseObj=urlopen(TmpRequestObj)
        TmpResponseHeader=TmpResponseObj.info().dict
        
        TotalBytes=int(TmpResponseHeader['content-length'])
        self.TotalBytes=TotalBytes
        TotalSegment=int(ceil(float(TotalBytes)/self.SegmentLength))
#        print ('Total length is '+str(TotalBytes))
#        print ('Total segment is '+str(TotalSegment))
        
        
        ReObj=re.compile(r'.*/(.*)')
        Matched=ReObj.search(self.FetchURL)
        if Matched:
            FileName=Matched.group(1)
            if os.path.isfile(FileName):
                self.FileObj=open(FileName,mode='rb+')
            elif not os.path.isfile(FileName):
                self.FileObj=open(FileName,mode='wb')
                self.FileObj.truncate(TotalBytes)
        ThreadForDiplayingSpeed=Thread(target=self.__DisplaySpeed)
        ThreadForDiplayingSpeed.start()
        
        CurrentIndex=0
        try:            
            while self.TotalByteOfDownloaded<TotalBytes:
                if str(CurrentIndex) in self.DictForDownloadingSegment or str(CurrentIndex) in self.ListForFinishedSegment:
                    CurrentIndex=((CurrentIndex+1)%TotalSegment)
                    continue
                elif (str(CurrentIndex) not in self.DictForDownloadingSegment) and \
                     (str(CurrentIndex) not in self.ListForFinishedSegment):
                    while True:
                        if len(self.DictForRunningThread)<self.ThreadPoolNum+1:
                            ThreadObj=Thread(target=self.FetchSegment,kwargs={'index':CurrentIndex,
                                                                              'length':self.SegmentLength})
                            ThreadObj.start()
                            CurrentIndex=((CurrentIndex+1)%TotalSegment)
                            sleep(0.1)
                            break
                        else:
                            sleep(2)
            self.FlagOfTerminated=True
            print ('Download finished')
        except KeyboardInterrupt:
            print ('Trigger terminated signal.......')
            self.FlagOfTerminated=True
        except Exception as e:
            print (e)
            self.FlagOfTerminated=True
        finally:
            sleep(3)
            self.FileObj.close()
#            print ('Cloced file object')
            
    def __DisplaySpeed(self):
        PrevDownloadedByte=0
        while True:
            sleep(1)
            if self.FlagOfTerminated or self.TotalByteOfDownloaded==self.TotalBytes:
                break
            Delta=self.TotalIncomeBytes-PrevDownloadedByte
            Speed=int(Delta/1)
            PrevDownloadedByte=self.TotalIncomeBytes
            BaseKB=1024
            BaseMB=1024**2
            BaseGB=1024**3
            Result=(str(Speed)+' B/s' if Speed<BaseKB else False) or \
                (str(Speed/BaseKB)+' KB/s' if Speed>=BaseKB and Speed<BaseMB else False) or \
                (str(Speed/BaseMB)+'MB/s'  if Speed>=BaseMB and Speed<BaseGB else False) or \
                (str(Speed/BaseGB)+' GB/s')
            print ('Current download speed is '+Result)

            
            
            
#### http://www.tutorialspoint.com/java/java_tutorial.pdf

if __name__=='__main__':
    Tmp=Downloader('http://cdn01.foxitsoftware.com/pub/foxit/reader/desktop/linux/2.x/2.2/en_us/FoxitReader2.2.1025_Server_x64_enu_Setup.run.tar.gz')
    Tmp.Run()
