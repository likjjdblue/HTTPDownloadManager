import socket
import select
import threading
import time

class Proxy:
    def __init__(self):
        self.LocalProxyAddr='0.0.0.0'
        self.LocalPorxyPort=8888
        self.TargetAddr='127.0.0.1'
        self.TargetPort=8088
        
    def Run(self):
        print ('main thread is running.......')
        self.ProxySocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM, 
                                      )
        self.ProxySocket.bind((self.LocalProxyAddr,self.LocalPorxyPort))
        self.ProxySocket.listen(5)
        while 1:
            ClientSocket,ClientAddr=self.ProxySocket.accept()
            SubThread=threading.Thread(target=self.__ThreadFunc,args=(ClientSocket,ClientSocket))
            SubThread.start()
        
    def __ThreadFunc(self,ClientSocket,ClientAddr):
        InSocketList=[]
        OutSocketList=[]
        ErrSocketList=[]
        
        TmpTargetSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            TmpTargetSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            TmpTargetSocket.connect((self.TargetAddr,self.TargetPort))
            InSocketList.append(TmpTargetSocket)
            OutSocketList.append(TmpTargetSocket)
            
            InSocketList.append(ClientSocket)
            OutSocketList.append(ClientSocket)            
        except Exception as e:
            print ('Error occured while initalization connection')
            print (str(e))
            return 1
                        
        try:
            while 1:
                ReadableList,WritableList,ErrorList=select.select(InSocketList, 
                                                                 OutSocketList, 
                                                                 [], 
                                                                 )
                RecvBuffer=''
                for read in ReadableList:
                    for write in WritableList:
                        if read is not write:
                            RecvMsg=read.recv(1024)
                            if  not len(RecvMsg):
                                print ('connection is closed')
                                raise Exception('Connection closed')
                            print ('going to forward datagram')
                            write.sendall(RecvMsg)
                            print ('finish to send datagram')                                                           
        except Exception as e:
            print ('INFO:'+str(e))
            
        print ('sub-thread is going to terminate')
            
            
ProxyObj=Proxy()
ProxyObj.Run()