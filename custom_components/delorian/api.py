import random
import pickle
from typing import Optional, List, Tuple

from datetime import datetime, timedelta

STATE = pickle.loads(
    b"\x80\x04\x95\x8f\x0e\x00\x00\x00\x00\x00\x00K\x03(J\xb3^\x1fe\x8a\x05!31\xc8\x00J\xe8/-cJ\x93\xb1NF\x8a\x05\xc4n\xdd\xba\x00\x8a\x052\x10\xea\xc1\x00\x8a\x05[\xa1<\xea\x00Jk\xe4\xb7OJ\xa2\x81\x9d\x1fJ\xdc\xe1\x81^\x8a\x05\xa8\xc4\x8b\xf2\x00J\xbb^\xf1\x1c\x8a\x05\x04\\+\xb2\x00J\xbc[\xb8QJQ\xff\xe4DJx\xab\x029J%\xc6\xf78J\xfe\x99\xf2\x06J\xc1\x1540\x8a\x05Kk\xc4\xd2\x00\x8a\x05R#\x86\xe1\x00\x8a\x05\x99uz\xd7\x00\x8a\x05\xf95\x8c\xb6\x00J<\xb29_J\xba\x8f\x8fNJ\x81\x03\xfc0\x8a\x05b\xe2\x8b\xfa\x00\x8a\x05\xc3\x15\xfb\xb9\x00\x8a\x05d\xb3\x84\x9a\x00\x8a\x05B\xd1S\xf6\x00J\n\x1f[:\x8a\x05\xb4R\xae\xe1\x00Jd\xdc\xa3KJo^\x13FJ\x85\xdf\x81,J\xf3/d`\x8a\x05\n\x94\x03\x93\x00JB\xdb\xf5-JR\x8cZ\x01J\xae\xfa\x1a\x19\x8a\x05(\xcb\x9a\xa8\x00J\xee\xde\xf8xJQ\xa0\x1eg\x8a\x05\xba\xc4\xa1\xee\x00\x8a\x05\x94;\xff\x97\x00J\xe9=\xca\x0fJ\xef\x83\x1f2Jr\x8c\x977\x8a\x05?\xcap\xc4\x00Jt\\t\x18J>9\xa4\x1fJ\xad\xd0\xbe\x0eJ\xa4>\x95?J\xa3q\x9fo\x8a\x05\xd5\xf2a\xaf\x00\x8a\x055\x18\xc4\x8d\x00\x8a\x05\x04\x17z\x94\x00\x8a\x05\x02F\x98\xb0\x00\x8a\x05\x9by\xc0\xac\x00\x8a\x05\x05A\x14\x96\x00J\x18\\\x0bD\x8a\x053,\x06\x8c\x00JU\xe0\xbf&\x8a\x05\xc1\xdc\xc7\x93\x00J\x90\x80w\x10J\xe5\x0b\xfd/Jh\"\xa5\x15JcFVRJG\xb7>\x07\x8a\x05\x96\xe4\x02\xcd\x00J\x8b\xbcn\x07J\xc1g\xf9AJ\x15\x95\xb6\x18Jc\x82_\x14J\x95:\xe9{J\xb5\x15\xb1\r\x8a\x05\x81k\x08\xf1\x00J\x0bn\"aJ\r0_\x1aJ\xaa\xf3CVJ?\xc5\xbb\tJ#{\x960J;r\xa5_\x8a\x05\x93`<\xa3\x00\x8a\x05B\xdf\xde\x88\x00J\xe3B\x1aVJ\x03i\xc6Q\x8a\x05\xa0\xbe\xae\x89\x00\x8a\x05\x1c\x0e\xdf\xca\x00JV\xd33\x15\x8a\x05\x04{e\x86\x00J\xca3\x007J8=\xba<\x8a\x05\xf5\xf4\x7f\xa3\x00J\xee)J\x12J`\xd7HR\x8a\x05o\x12\x81\x8b\x00\x8a\x05y9\xd7\xbb\x00JNL\xcf(\x8a\x05\x9e7\xc3\xb9\x00J\xd5\x02i\n\x8a\x05\xf9\xaf\x08\xe5\x00\x8a\x05\xca\x7f\xc1\xef\x00\x8a\x05S2\xd7\xe2\x00\x8a\x05\xd8:\xb1\xd7\x00J\x04\xfc\xa4Z\x8a\x05m\x10A\xa8\x00\x8a\x05\xd4\xddP\xc2\x00\x8a\x05\x1d\x8f\x83\xe2\x00\x8a\x05\xf2\xec\xb5\xc9\x00\x8a\x05\xe0\xd5\xa4\x84\x00Jm\xcd\xc1x\x8a\x05\xf5d\x8b\xb1\x00J\xde\xc0xs\x8a\x05\x16\xdf\x9c\xf8\x00J<\xa8\xa1m\x8a\x05{\xfdY\x8d\x00JW\x14\t\x12JY\xac*\x1bJ\xbc\x98\x0b\x01Jv\xc8\xae4J\xab\xce_%\x8a\x05J\x8f_\x88\x00\x8a\x05\x0b\xa7c\x9b\x00\x8a\x05\xaf\xea\xad\x91\x00\x8a\x05nR\r\xf5\x00J;\xc8\x93\x13J\xaaSr!J+r\xa5NJ*\x16\x99{J\\\x8620\x8a\x05\xc1\xea\xce\xf2\x00\x8a\x05\x1b-s\xcb\x00\x8a\x05\xbb\xb6e\xa3\x00\x8a\x05\xc0\x1a\\\xa8\x00J\xe0\x08~u\x8a\x05\xd3\r\xf4\x9f\x00\x8a\x050\xec9\xba\x00J\xc6\xe1En\x8a\x05f\xfd\x87\xe3\x00J\xf5\xee\x032Je\xbb\xe0xJQ\x1b\\\x0c\x8a\x05+T\xe3\xbd\x00J\xee\r\xc0dJ\xc9_h\x03J\xda\x14\x03.\x8a\x053\x9e\xc9\xee\x00\x8a\x05\xa7B\x88\xd7\x00\x8a\x05v\x89\xc4\xa1\x00\x8a\x05C:-\xd4\x00\x8a\x05,9I\xfc\x00\x8a\x05{\xb9\xcb\xab\x00\x8a\x05\x00\xf4\xbb\xe0\x00\x8a\x05\xf9/x\x9c\x00J\x8el\x9d\x15J9\xe0\xf8\x0f\x8a\x05v\xb2\xb3\x8f\x00\x8a\x05`\xbes\x8a\x00\x8a\x05zk7\xcb\x00J\xae\xbb\x10jJY\xe9P\x1dJ\x8e\xa0zaJ\xce\n\xb6-\x8a\x05}\x88\x8b\xdd\x00J\xdc\xe4\xe1K\x8a\x057+\"\xc4\x00Jc#\x94iJ\xb5M(\x15J\x02O\xc0EJ1\xfa;7\x8a\x05+T\xa5\xed\x00\x8a\x05VhO\xfd\x00\x8a\x05\x98\x87\xa1\xb2\x00\x8a\x05\xcaR=\xff\x00\x8a\x05\x8d\xd2\x89\xf8\x00J\x0e+r\x00J\x19\xca\x06\x0f\x8a\x05\t\x18\xea\xd5\x00\x8a\x05\x9f\x8a\x9c\xe3\x00J\xd7$\xc2E\x8a\x05@7\xfa\xf3\x00\x8a\x05\r\xe4\xdb\xff\x00\x8a\x05Sr!\xe1\x00JE\xb7KZ\x8a\x05\xaf,\xb3\xeb\x00\x8a\x05qQ'\xf8\x00\x8a\x05_\xd7=\xdc\x00\x8a\x05;\xc3(\x99\x00J\xf7\xcd\xd5*\x8a\x05\x07}\xff\x92\x00J\xd4\xf16RJa\x80\x92\x10\x8a\x05\x15\xbbu\xf9\x00\x8a\x05\x1f\xcc\xc8\xf2\x00Jx\xce3MJ\x99<\x8c8\x8a\x05\xa1\x9e\x89\xac\x00\x8a\x05t\x99Y\x9c\x00J\x85\xca\x81ZJ\xb1\xfe\x00J\x8a\x05\xa9\x80\xf8\xc0\x00J\x0cT\xf50Jf\xfd\xd8vJ\xc5\xcbvvJ\x9d\x99=\x0c\x8a\x05Y\xf6\t\xf3\x00\x8a\x05t\xc5\xfd\xc9\x00J*\xb9\xe0HJ\xdb\xa8\xd6\x0b\x8a\x05K\x8c\x02\x92\x00\x8a\x05Tk\x82\x88\x00J\xe3_RsJ\xf4\x7f\x1fx\x8a\x05\xf8\xa3\xdb\xd7\x00\x8a\x05\xbb\xbae\xb5\x00J\xb6\xc6\xd5\x14\x8a\x05\x1c\xbdj\x88\x00J\x91\xb4\xcb\x1fJ\x9dwS\x04\x8a\x05\xc1L\xdf\xdd\x00\x8a\x059\xec8\xfd\x00J\xcb',&\x8a\x05ZQ\xdd\xb3\x00J1\x83\x17aJ\x17\xe7DtJ?\xa3~\x15\x8a\x05T\x11\xc9\xdb\x00\x8a\x05\x89\xadb\xff\x00J\xb1\xde\x0f\x07J\xcd.c7JQ\x94\xef\x16J\xdc/\x07<\x8a\x05\xd43L\xd5\x00J\x1e\xef\xcf9\x8a\x05d\xf2F\x87\x00\x8a\x05[\xc3\xe4\xdf\x00J\x8a\x9b\x1f\x14J\x87T:sJ\xf4QDG\x8a\x05\x18\x0b\xac\xbe\x00J$R\xaa\x0e\x8a\x05\x05\xaf?\xa4\x00\x8a\x05\x00~\xd3\xf7\x00\x8a\x05>^\xa2\xf6\x00J\x98zX,\x8a\x05\xe0\xd1<\xae\x00\x8a\x05\x95\xe6\x9c\xaf\x00J\x01\"\xc2|\x8a\x05\xca*4\xb7\x00J5\x86\xcbpJ\xe2\x01x\x04\x8a\x05\xb6\xda\xda\xf4\x00JY\xeaX\\\x8a\x05`@\xe9\x85\x00J\x88|\x97'\x8a\x05Y\xfb\xab\xf9\x00J$V4AJ\x94\xb9K,\x8a\x05\r\x879\x98\x00J\xaf^\x92xJ\xb3\\\xffo\x8a\x05\x8d\xc3{\xf9\x00\x8a\x05\xaf\xb0\xc1\xe0\x00\x8a\x05'\x92\xc6\xe8\x00\x8a\x05M\x98\x14\xdf\x00\x8a\x05%\xa1_\xb9\x00JK\x071B\x8a\x05\xf1]/\xda\x00J\xf2\x01rI\x8a\x05\x1a\xb7\xd2\xb9\x00\x8a\x05\xe8\xfd\xaa\xdb\x00\x8a\x05S\xdd\xb1\x82\x00\x8a\x05\xb3#\xc2\x84\x00J\xa0\x13\x830\x8a\x05\xd2\xe3h\xed\x00J\x170E?\x8a\x05V\xf9\xe7\xcb\x00\x8a\x05\xc3\x02\xee\xd2\x00J\xa4A\xb6R\x8a\x05\x17\x8f\xc3\xac\x00J7\x8d\t\x1b\x8a\x05\xb5\xc4(\x89\x00\x8a\x05S|\x8a\xc5\x00\x8a\x05\xef\x08\xda\xdc\x00\x8a\x05\x9d\xf6\xce\xa6\x00J\xe2@\x1fgJ\xd8\xb9\xa7I\x8a\x05U\xbd\xf4\xad\x00J\xcc\x04''\x8a\x05\x0f\x8f[\xf3\x00\x8a\x05\x0cD5\x84\x00J\x08@lLJ3\xdc\x8b\x13\x8a\x05\x9czq\xb5\x00J\xf0\t\xc0YJ\x15\tfM\x8a\x05\x93\x94\xc4\xb3\x00\x8a\x05M\n\xd4\xa5\x00\x8a\x05?\xcc#\xe8\x00J\x80\xbe\xeckJaO\xaax\x8a\x05\xa2\xddZ\x95\x00J\xf6C\x0b4Ja[\xd7\x0eJ\xe8\xa3\xa2'Jf\xc9\x08\x0eJ\xc1J\xe9t\x8a\x05)\xdc\x0b\x83\x00J\x90\x87\xc7/Jv\xf1\x85\x17\x8a\x05B\xf5K\xae\x00\x8a\x05\xa9\x97n\xfe\x00J\x98[\x8al\x8a\x05\xf1\x90R\x99\x00J\xd0\xa9\xf2\x06J`\xc1\x8d-J\x1a\xad\x1d\rJpw-J\x8a\x05;k*\xf3\x00J\x80F\x95vJ\x17\x18L(\x8a\x05\xdc\x1eT\x98\x00\x8a\x05Uxx\x96\x00J\xc9C\xddZJ\x95p}N\x8a\x05\xb6\xb7\xd6\xf3\x00\x8a\x05\x05#\xa3\xbf\x00J\x92\xaa\xfd*\x8a\x05R\x9d\x02\xc2\x00J\x9dw\xb8\x1fJ=\xd9\x88^\x8a\x05\x1aZX\xcb\x00JBy\xf2\t\x8a\x05\rq\x88\x8b\x00\x8a\x05m\xf6\xcb\xd7\x00\x8a\x05\xc9\xa7\x85\xf8\x00J>\xe8\xbd-JL\xed\xb5LJaf\x11/JV\xadT\x0c\x8a\x05\xa5wZ\xb7\x00\x8a\x05\xf9\xfd\xfe\xba\x00J\xe9\x00\xb5[\x8a\x05\xda\x9c\x8e\xe0\x00J*\x96\xb9H\x8a\x05\x90\xfb\x02\x91\x00J\x93\x1a\x89]J\x15\x99w\x02\x8a\x05:\xef\xbb\x99\x00J\x03\x1d\xf0\x10\x8a\x05\xa3s\x1b\xa3\x00J\xbeu\x9b$\x8a\x05\"\xaa\xd6\xf2\x00\x8a\x05(I\x00\xec\x00\x8a\x05S\xf6\xcf\xa3\x00J\xcb\xb7\xe6S\x8a\x05\xf4@\x03\x92\x00\x8a\x05\xc9'\x18\x86\x00Jn\xd1\x97@\x8a\x05I\x11\x86\x99\x00Jm\xc2L?J\xb8;+\x16\x8a\x053-\x19\x9b\x00J7\x04\x0flJ[U\xf60J\xb3\x95:lJ\xac\x8c\xa1|\x8a\x05M\xf9t\xca\x00J(\xc5@%\x8a\x05\xbeT\x9d\x9b\x00Jn\x85(hJR\xb2\x7f\x05\x8a\x05i\xcc\x97\xf9\x00\x8a\x05\x00\x87\x9e\xf3\x00\x8a\x05\x84lG\xf4\x00J\xcdM6W\x8a\x05;\xfa\x1d\xd6\x00\x8a\x05\xbd\x81\xd3\xb6\x00\x8a\x05\x8e\xd8\xfa\x82\x00Jb\x1dG*\x8a\x05\xed\x83\xe6\xd7\x00\x8a\x05\xf4\x02\xa8\xf8\x00\x8a\x05S\xb9\xe3\x95\x00JoeU/\x8a\x057\x7f\xb7\xf6\x00\x8a\x05\x0e\x87\x97\xfb\x00JI\x08\xfbwJ\x82o\xfao\x8a\x05\x8c\xedr\x81\x00J\x8b\x1d$v\x8a\x05p7\xb3\x8e\x00\x8a\x054\xc1\xf3\xd1\x00\x8a\x05T\xe9\xff\xbd\x00J2c\"XJ\x9c\x91\x80x\x8a\x05S\xea\xe4\x82\x00\x8a\x05m\x86Z\xb5\x00\x8a\x05q)\xc8\xba\x00\x8a\x05@\x14\xf1\xdf\x00\x8a\x05\xbbji\x84\x00J\x14\xcc\x103JSTB\\J\xb6G9v\x8a\x05[\xca\xde\xa5\x00\x8a\x05\x84)\x8e\xb7\x00J\xc2\xb7\xef.Jx\x9b~oJ\xb0_\xfan\x8a\x05\xb5\x03x\x9e\x00JV\xe9\xb28\x8a\x05/X=\xc2\x00J\xd7 \x1d\"\x8a\x05\xc4\xd6`\xda\x00J\xcd\x17\x10\x16J\xc6\xc07 J\x92\x1d\xedqJ\xa0\xe7\x1f\x08Jk\xde\xaf\\\x8a\x05\xeb?#\xfd\x00J/\xd1\xca/J\x9a\xf7d|J\x04\xe4Ke\x8a\x05v\xf7H\xd2\x00\x8a\x05(\x9a\x17\xb3\x00J\x7f\xc0\xbcDJ\xfa\xd3\xe3OJ\x99\xa5/\x18\x8a\x05V(\xab\xab\x00\x8a\x05\\\xcbK\xa3\x00\x8a\x05N\x9d\xbf\xb3\x00J\r\x01\xa0\\\x8a\x05{+\xf8\xe4\x00\x8a\x05\xb8\xaa\xe9\xd4\x00\x8a\x05~\xd1\xa2\xf0\x00J\xc87\tu\x8a\x05F@\xe8\x88\x00J\x8f\xdd\xb5\x1d\x8a\x05+S\x8e\xa8\x00\x8a\x05\x89\xba\xfb\x8e\x00\x8a\x05'\xa2\x17\xa0\x00\x8a\x05\nN\x1f\xb2\x00J\x9d=,\x02\x8a\x05\xca\x87\xfd\xe2\x00J3\x9d2<J\x04\x10\xe8b\x8a\x05\xe9\xd4\x9d\xfe\x00\x8a\x05\x80\xe1>\x86\x00\x8a\x05\x97\\\xd4\x83\x00J\x0c\xe8wEJ\x8fF. \x8a\x05\xbc\xd8i\xcc\x00Jl\xb5\xc4\x14\x8a\x05^\x85r\xa8\x00\x8a\x05|x\xaa\xd2\x00J\xa3n\x15\x0b\x8a\x05\"\xa8\x85\xc4\x00J~\xa5\xfc,J\xd1\xaf\xdf\x10J\x82d\xb1{\x8a\x05:\xa0\xe3\x8f\x00\x8a\x05\x9f\xc4G\x90\x00\x8a\x05\x11TO\xaf\x00\x8a\x05\x84\\\xa2\xfe\x00\x8a\x05X\xbd\xb9\xc6\x00J\xa8?k4JY\x12\xac\x11\x8a\x05\x02;E\xe6\x00JY\xf7goJ\xb2\x9d+\x04\x8a\x05\xb66T\xc3\x00\x8a\x05<\xe6\x05\x80\x00J\x87\xef\xad)\x8a\x05\xa5\x075\x86\x00\x8a\x05e\xfb`\xd1\x00J\xce+\xae\x1a\x8a\x05\xb6\xcb\xe0\x8b\x00Jc\xdeIW\x8a\x05\xf6\\\xfc\xc7\x00\x8a\x05\xbds\xeb\x9f\x00J\"\xbfnkJ\xf3\xc3\x1a<\x8a\x05\x9aM\xf7\xfe\x00J\xdd\x85\x07\x10\x8a\x05\x18\xa5\xcb\xc6\x00\x8a\x05Q\x90\xc5\x87\x00J\x89\x0c\x1e\x1bJ\xa1\xcf?c\x8a\x05A;\xb7\xa7\x00\x8a\x051\x9d\x86\xbf\x00Jq.`vJ\xc0=!zJ\xdbi\x825\x8a\x05\xddGV\xe4\x00J\xd5\xbf\xcdEJ$9\xe1\x11\x8a\x05\x8f4\x9a\xfe\x00\x8a\x05\xeb\x8c@\xce\x00J\x9d\xbbh\x00J\xf1BMf\x8a\x05O\xde^\x95\x00J\xa4\xf4yE\x8a\x05\x01\xb7\x06\xcd\x00J\xf0\x8d\xa0>\x8a\x05 \xdb\x88\x94\x00J5?\x90)J\x121\xb4\x19\x8a\x05\xaa\x1a5\x82\x00J\x05G\xb28\x8a\x05\xc2\x0c\xb5\xeb\x00J\xe3\xf1\xd8\x11\x8a\x05\xcfD\xe8\xb1\x00J\x9c[\x0e&\x8a\x05&\x8d5\xf7\x00\x8a\x05?r(\xe5\x00J\x87\xc8-sJ\xc8_y\x0eJ\x07KmN\x8a\x05\xb8\xd7B\x81\x00J\x13&*MJ\xc1\xf0\xddRJ\xca\xf4\x13\x07\x8a\x05[\xea\xa9\x85\x00J|\xc9h+J\x12a\xbb\x04\x8a\x05*\xd7\xe7\xc2\x00J\x85\xf26$\x8a\x05Dx\x1e\xc3\x00\x8a\x05\xaaz\xe2\xbf\x00JJ\x17\x03\x11J\xa3h\x91BJ\xfe\xdcY3\x8a\x05Y\xde\xf5\xec\x00\x8a\x05\x10(h\x98\x00J\x96\xaf\x10HJ\x8cP-\x1b\x8a\x05 \xcb\xa3\xa1\x00J\x1f\x06\xab}J\x0f\xbd\xaeoJ\xf2pb'JZ\xca\xc4HJ\xe1k\x98^J\x99\xcb\x94!\x8a\x05\xb1\xc32\xbc\x00\x8a\x05-\x0cO\x9b\x00J\x9a\xfd\xb6?\x8a\x05V\xd3\xa2\xd9\x00\x8a\x05\xd8\x1b1\xdd\x00J\xb6\x8b\xbf,J.\xdc\x15TJ\xf5:\xa6-J\xfa}\xac\x07J%\x05\xd1NJ\x88s9z\x8a\x05\xae\xb7\xc2\xa1\x00\x8a\x05\x82\x92\xed\xf5\x00\x8a\x05/\x83\x88\x81\x00J`v2\x1fJM\xe6\xbe\x1eJuzLFJ5\x91\x13!\x8a\x05\xe7\x98\x14\xac\x00J\xeb\xd4\xf2x\x8a\x05\xdb\x9aO\xcb\x00\x8a\x05<\xed\xcf\xb0\x00\x8a\x05B\x16X\xb3\x00\x8a\x05#z\xe8\xaf\x00\x8a\x05\x15\xff\xa6\xb8\x00J\x95I\x1dJ\x8a\x05(\xbfl\xb6\x00\x8a\x05\xef8\xec\xa7\x00\x8a\x05\xec\x12\xed\xf0\x00\x8a\x05\xae\xc8\xff\xcf\x00\x8a\x05\x11\xc4\x00\x8c\x00J\xea&\x04wJ]\xb6M\x17J\xeft\xe3\x1e\x8a\x05b\x98\xbf\xea\x00J\x0f\xb3YPJ\xd36\xc1KJ\x0e2\x1a\x01J}1p\x11J\xf0\xe4\xd9NJ\x08\x19\x00 J\xc3T\xd3DJ\xa2\x1b\xe0\x03\x8a\x05\x9a\xef\xc9\x89\x00J|\x11gVJ\xfd\xc1\xfc\x13J?Z\x00wJ%\xbemWJ\x8e\xaau6J\xb4\x1am:\x8a\x05\x90\x7f\xd0\xba\x00J\xc1\xb8\r\x1e\x8a\x05\xd2\xbec\xb7\x00\x8a\x05 &\x07\xf9\x00J\xe7\xcd\x81g\x8a\x05\xb1\xee\xba\xa6\x00\x8a\x05\xe0\xf8\xf7\xfc\x00J\x01\x01\xf1=\x8a\x05\x02\xf8\x00\xb3\x00JsX\xcc~\x8a\x05!\xfe1\xfe\x00J\xd9\xd2\xc1)\x8a\x05R\x85g\x85\x00\x8a\x05\x00V\x9d\xc9\x00J_X\xd6gJ\x9e\x03\xa0XJ.\x8c\xc5V\x8a\x058w2\x83\x00\x8a\x05\x83\x82z\xc2\x00J\xe3\xa4\xd6m\x8a\x05\x18\x9e\\\xa9\x00J\xc22_F\x8a\x05\xdb\x0fR\xc6\x00\x8a\x05\xd7\xe1\xda\xe9\x00J]\xbd%\x12\x8a\x05\xfe\xed!\xf5\x00J\xe2\xae-\x14Js\x8e\xe9A\x8a\x05J\x87\x9d\xd6\x00\x8a\x05\x1bWX\xb8\x00J\xd5\xf5ciK\x05t\x94N\x87\x94."  # noqa: E501
)


class API:
    def __init__(self):
        self.r = random.Random()
        self.r.setstate(STATE)

    def fetch(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: Optional[timedelta] = timedelta(hours=1),
    ) -> List[Tuple[datetime, float]]:
        def g(start: datetime, end: datetime, step: timedelta):
            cur = datetime(year=2022, month=7, day=1)
            while cur <= end:
                v = (cur, self.r.randint(10, 300) / 100)

                if cur >= start:
                    yield v

                cur = cur + step

        end = end or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = start or end - timedelta(days=30)

        return list(g(start, end, step))  # type: ignore[arg-type]