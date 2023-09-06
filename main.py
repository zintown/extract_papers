import re

import requests

import csv

from lxml import etree
from lxml.etree import HTMLParser
import argparse
import os

from fake_useragent import UserAgent
import time

# only string means conf name is same with publisher name
# (["","","",...],"") means there is multiple sub conf with same publisher name
# ("","","") means there is multiple sub conf with it's own publisher name
# (num,["","","",...],"") means there is a series part of one conf, part-1 ... part-num 
A_CONF_LIST = [
    # safety A
    'ccs'   ,'sp'    ,'uss'   ,'ndss'   ,
    # safety B: esorics devide into three parts annualy
    'acsac' ,(6,['esorics'],'esorics'),
    'csfw'  ,'dsn'   ,'raid'  ,
    # architecture A
    'dac'   ,'hpca'  ,'micro' ,'sc'     ,
    'asplos','isca'  ,'usenix','eurosys',
    # architecture B: hipeac has sub confs parma dronese ngres | codesisss is new name of codes
    'fpga'  ,'cgo'   ,'date'  ,'cluster',
    'iccd'  ,'iccad' ,
    ('codesisss','codes'),
    (['parma','dronese','ngres'] ,'hipeac' ),
    'sigmetrics',
    'pact'  ,'vee'   ,'hpdc'  ,'itc'    ,
    'rtas'  ,
    # software A: pldi,popl,oopsla,icfp were included in journal pacmpl
    'pldi'  ,(['fse'],'sigsoft') ,'sosp'  ,(['ase'],'kbse'),
    "icse"  ,"issta" ,"osdi"  ,
    # software B: esop and fase are sub conferences of etaps | hotos conf seems strong related
    ('esop','fase'),
    (["icpc"] ,'iwpc'  ),(["lctes"],'lctrts'),
    (["saner"],'wcre'  ),(["icsme"],'icsm'  ),
    "issre" ,"hotos" ,
]
      
A_JOURNAL_LIST = [
    # pe journal divide one year's volume into two rows on the web html
    # jpdc journal has multiple volumes annually, so we need loop this journal's urls
    # tissec is tops's old name, dblp hasn't change it
        'pacmpl',
        # safety
        'tdsc'  ,'tifs',
        'tissec','compsec','dcc','jcs','scp',
        # architecture
        'tocs'  ,'tcad'  ,'tc'  ,'tpds'  ,'taco' ,
        'todaes' ,'tecs' ,'trets','tvlsi',
        'jpdc'   ,'jsa'  ,'pe'   ,
        # software
        'toplas','tosem','tse',
        'ase'    ,'ese'   ,'iet-sen','infsof',
        'jss'    ,'scp'   ,'stvr'   ,'spe'
]

def parse_conf_publisher(ele):
    urls = []
    publisher_name = ''
    if type(ele)==type(''):
        urls.append("https://dblp.org/db/conf/%s/%s%s.html" % (ele, ele, args.time))
        publisher_name = ele
    elif type(ele)==type(()):
        if type(ele[0]) == type(""):
            for e in ele:
                urls.append("https://dblp.org/db/conf/%s/%s%s.html" % (e, e, args.time))
                publisher_name = publisher_name + e + "|"
        elif type(ele[0]) == type([]):
            for e in ele[0]:
                urls.append("https://dblp.org/db/conf/%s/%s%s.html" % (ele[1], e, args.time))
                publisher_name = publisher_name + e + "&"
        elif type(ele[0]) == type(0):
            for i in range(1,ele[0]):
                for e in ele[1]:
                    urls.append("https://dblp.org/db/conf/%s/%s%s-%s.html" % (ele[2], e, args.time,i))
                    publisher_name = publisher_name + e + '|'
        
    print("Looking for papers from {} {}, keyword: {}\n exclude_keyword: {}".format(publisher_name, args.time, args.keyword, args.excludekeyword))
    return urls,publisher_name

def parse_journal_publisher(ele):
    url = 'https://dblp.uni-trier.de/db/journals/%s/index.html' % ele
    print("Looking for papers from {} {}, keyword: {}\n exclude_keyword: {}".format(ele, args.time, args.keyword, args.excludekeyword))
    return [url]

# input: urls list output: htmltext list
def getHTMLText(urls,name):
    and_flag = name.split("&")
    or_flag  = name.split("|")
    html_list = []
    ua =  {"user_agent": UserAgent().chrome}
    attempt = 5
    for i in range(len(urls)):
        for retry_nums in range(attempt):
            try:
                r = requests.get(urls[i],headers = ua,timeout=1000)
                r.raise_for_status()
                r.encoding = r.apparent_encoding
                html_list.append(r.text)
                break
            except:
                if len(and_flag) <= len(or_flag):
                    continue
                else:
                    if retry_nums < attempt - 1:
                        continue
                print("get html failed")
                return None
    return html_list

def writeToCsv(file_path, dicts, name):
    with open(file_path,'a',encoding='utf-8',newline='') as f:
        csv_write = csv.writer(f)
        csv_head = ["==========",name.upper(),"TITLE".upper(),"AUTHORS","URL","==========="]
        csv_write.writerow(csv_head)
        for ele in dicts:
            csv_write.writerow([ele['title'],ele['url']," "," ".join(ele['authors'])])

def extract_conf_papers(urls, name, file_path):
    htmltexts = getHTMLText(urls,name)
    if not htmltexts:
        dics = [{'title':f"curr years had no {name} conf", "authors":"", "url":""}]
        writeToCsv(file_path, dics, name)
        return
    for htmltext in htmltexts:
        try:
            parse_html = etree.HTML(htmltext, HTMLParser())
        except:
            print('Failed! Please check the conference name ,conference year and the keyword!')
            exit(1)
        dics = []
        try:
            cata_xpaths  = parse_html.xpath('//header[@class="h2"]')
        except:
            print("get catagory head of conf papers failed")
            exit(1)
        print(f"Number of catagory in \"{name}\" conf: {len(cata_xpaths)}")

        try:
            cata_paper_xpaths = parse_html.xpath('//ul/li[@class="entry inproceedings"]/..')
        except:
            print("get each catagory's papers failed")
        print(f"Number of catagory's corrsponding paper group in \"{name}\" conf: {len(cata_paper_xpaths)}")

        if len(cata_xpaths) == 0:
            cata_flag = False
        else:
            cata_flag = True

        try:
            parse_xpaths = parse_html.xpath('//li[@class="entry inproceedings"]')
        except:
            print("get entry of each conf paper failed")
            exit(2)
        print("Number of \"{}\" conf papers(all fields): {}".format(name, len(parse_xpaths)))
    
        for ind in range(len(cata_paper_xpaths)):
            cata_papers_str = etree.tostring(cata_paper_xpaths[ind])
            cata_papers = etree.HTML(cata_papers_str, HTMLParser())
            try:
                cata_papers= cata_papers.xpath('//li[@class="entry inproceedings"]')
            except:
                print("get exact paper line failed")
                exit(1)

            if cata_flag == True:
                if ind < len(cata_xpaths):
                    cata_names_str  = etree.tostring(cata_xpaths[ind])
                cata_name  = etree.HTML(cata_names_str, HTMLParser())

                try:
                    cata_name = cata_name.xpath('//h2')[0].text
                except:
                    print("get catagory of conf papers failed")
                    exit(1)
                dic = { "title": "--------catagory name is: {}".format(cata_name).replace("\n"," "), "authors": "", "url": "--------"}
                dics.append(dic)

            for cata_paper in cata_papers:
                cata_paper = etree.HTML(etree.tostring(cata_paper),HTMLParser())
                try:
                    paper_attr = cata_paper.xpath('//cite//span[@itemprop="name"]')
                except:
                    print("get current one conf paper title failed")
                    exit(1)
                
                paper_url = cata_paper.xpath('//div[@class="head"]/a/@href')[0]

                parse_content = [paper_attr[idx].text for idx in range(len(paper_attr))]
                if parse_content[-1] != None:
                    paper_title  = parse_content[-1].upper()
                else:
                    print("TITLE_GREP_FAILED")
                    paper_title  = "TITLE_GREP_FAILED"
                paper_author = parse_content[:-1]
                grep_keyword(dics,paper_title,paper_author,paper_url)

        writeToCsv(file_path, dics, name)
        print("The number of Conf Papers extracted: {}".format(len(dics)-len(cata_xpaths)))

def extract_journal_papers(url, name, file_path):
    htmltext = getHTMLText(url,name)
    if not htmltext:
        dics = [{'title':f"curr years had no {name} conf", "authors":"", "url":""}]
        writeToCsv(file_path, dics, name)
        return
    htmltext = htmltext[0]
    #Try to get one year's multiple volume sub page
    matchObj = re.match(r'.*<li><a href="(.*)">Volume .*[,:] (\d+/)?%s</a></li>.*' % args.time, htmltext, re.DOTALL)
    if not matchObj:
        all_urls = re.findall(r'<li>%s: Volumes\n(?:<a href=".*">.*</a>,?\n)*</li>' % args.time, htmltext)
        #print(f"all_urls is {all_urls}")
        urls = []
        for u in all_urls:
            #print(f"u is {u}")
            part_url = re.findall(r'https://dblp.uni-trier.de/db/.*.html',u)
            urls.extend(part_url)
        #print(f"urls is {urls}")
    else:
        urls = [matchObj.group(1)]
    dics = []
    # We have got multiple sub pages(volumes), and try to reslove them
    htmltexts = getHTMLText(urls,"")
    for htmltext in htmltexts:
        try:
            parse_html = etree.HTML(htmltext, HTMLParser())
            parse_xpaths = parse_html.xpath('//li[@class="entry article"]')
        except:
            print('Failed! Please check the journal name ,conference year and the keyword!')
            exit(1)
        print("Number of \"{}\" papers(all fields): {}".format(name,len(parse_xpaths)))
        for parse_xpath in parse_xpaths:
            parse_html_str = etree.tostring(parse_xpath)
            parse_html1 = etree.HTML(parse_html_str, HTMLParser())
            paper_url = parse_html1.xpath('//div[@class="head"]/a/@href')[0]
            parse_content = parse_html1.xpath('//cite//span[@itemprop="name"]')  
            parse_content = [parse_content[idx].text for idx in range(len(parse_content))]
            if parse_content[-1] != None:
                paper_title  = parse_content[-1].upper()
            else:
                print("TITLE_GREP_FAILED")
                paper_title  = "TITLE_GREP_FAILED"
            paper_author = parse_content[:-1]
            grep_keyword(dics,paper_title,paper_author,paper_url)

    writeToCsv(file_path, dics, name)
    print("The number of Journal Papers extracted: {}".format(len(dics)))

def grep_keyword(dics,paper_title,paper_author,paper_url):
    if args.keyword:
        for i in range(len(args.keyword)):
            if paper_title.find(args.keyword[i]) != -1:
                # print(parse_content[-1])
                for j in range(len(args.excludekeyword)):
                    if paper_title.find(args.excludekeyword[j]) != -1:
                        return
                break
            elif i == len(args.keyword) - 1:
                return
    dic = {"title": "* %s" % paper_title, "authors": paper_author, "url": paper_url}
    dics.append(dic)
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Conference Information")
    # parser.add_argument('-n',"--name", type=str, required=True,help="Name of Conference you want to search.")
    parser.add_argument('-t',"--time", type=int, default=2022, help="Year of Conference you want to search.")
    parser.add_argument("--save_dir", type=str, default=None, help="the file directory which you want to save to.")
    parser.add_argument('-k',"--keyword", type=str, default=None, help="the keyword filter file, if None, save all the paper found.")
    parser.add_argument('-n',"--excludekeyword", type=str, default=None, help="the keyword reverse filter file, if None, not exclude any paper")
    args = parser.parse_args()

    if args.keyword:
        with open(args.keyword,'r',encoding='utf-8') as f:
            args.keyword = f.readline()
            args.keyword = list(args.keyword.upper().split(","))
    else:
        args.keyword = ""

    if args.excludekeyword:
        with open(args.excludekeyword,'r',encoding='utf-8') as f:
            args.excludekeyword = f.readline()
            args.excludekeyword = list(args.excludekeyword.upper().split(","))
    else:
        args.excludekeyword = ""

    if not args.save_dir:
        args.save_dir = '.'
    else:
        if not os.path.exists(args.save_dir):
            os.mkdir(args.save_dir)

    local_time = time.localtime(time.time())

    conf_file_path = os.path.join(args.save_dir,"conf_{}_{}_{}_{}_{}_{}.csv".format(args.time,len(args.keyword),len(args.excludekeyword),local_time.tm_year,local_time.tm_mon,local_time.tm_mday))
    journal_file_path = os.path.join(args.save_dir,"journal_{}_{}_{}_{}_{}_{}.csv".format(args.time,len(args.keyword),len(args.excludekeyword),local_time.tm_year,local_time.tm_mon,local_time.tm_mday))

    if os.path.isfile(conf_file_path):
        os.remove(conf_file_path)
        #print(f"{conf_file_path} deleted.")
    if os.path.isfile(journal_file_path):
        os.remove(journal_file_path)
        #print(f"{journal_file_path} deleted.")


    with open(conf_file_path,'a',encoding='utf-8',newline='') as f:
        f.write("args.keyword is: %s\n" % args.keyword)
        f.write("args.excludekeyword is: %s\n" % args.excludekeyword)

    for ele in A_CONF_LIST:
        urls,name = parse_conf_publisher(ele)
        print("Parsing URL: {}".format(urls))
        extract_conf_papers(urls, name, conf_file_path)

    with open(journal_file_path,'a',encoding='utf-8',newline='') as f:
        f.write("args.keyword is: %s\n" % args.keyword)
        f.write("args.excludekeyword is: %s\n" % args.excludekeyword)

    # Journal
    for ele in A_JOURNAL_LIST:
        url = parse_journal_publisher(ele)
        print("Parsing URL: {}".format(url))
        extract_journal_papers(url, ele, journal_file_path)

