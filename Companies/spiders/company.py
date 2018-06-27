# -*- coding: utf-8 -*-
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from pyquery import PyQuery as pq
import re
from ..items import *
import math
import time
from pymongo import MongoClient

class CompanySpider(scrapy.Spider):
    name = 'company'
    domains = ['www.qixin.com/']
    start_urls = ['https://www.qixin.com/company/9eda1ceb-4d50-4b02-9ef0-ad1437d24f75']
    max_depth = 2


    def parse(self, response):
        # 爬取工商信息---------------Done
        icinfo = response.css('#icinfo')
        company_key = icinfo.xpath('.//tr[1]/td[2]/text()').extract_first()
        if company_key is None:
            return None
        elif 'company_key' in response.meta:
            company_key = response.meta['company_key']

        company_item = CompanyItem()
        company_item['_key'] = company_key
        company_item['company_name'] = icinfo.xpath('/html/body/div[3]/div/div/div[2]/div/div[1]/h3/text()').extract_first()
        company_item['credit_code'] = icinfo.xpath('.//tr[1]/td[2]/text()').extract_first()
        company_item['organization_code'] = icinfo.xpath('.//tr[1]/td[4]/text()').extract_first()
        company_item['registration_number'] = icinfo.xpath('.//tr[2]/td[2]/text()').extract_first()
        company_item['operning_state'] = icinfo.xpath('.//tr[2]/td[4]/text()').extract_first()
        company_item['industry'] = icinfo.xpath('.//tr[3]/td[2]/text()').extract_first()
        company_item['establishment_date'] = icinfo.xpath('.//tr[3]/td[4]/text()').extract_first()
        company_item['company_type'] = icinfo.xpath('.//tr[4]/td[2]/text()').extract_first()
        company_item['business_term'] = icinfo.xpath('.//tr[4]/td[4]/text()').extract_first()
        company_item['legal_man'] = icinfo.xpath('.//tr[5]/td[2]/a[1]/text()').extract_first()
        company_item['registered_capital'] = icinfo.xpath('.//tr[5]/td[4]/text()').extract_first()
        company_item['registration_authority'] = icinfo.xpath('.//tr[6]/td[4]/text()').extract_first()
        company_item['company_address'] = icinfo.xpath('.//tr[7]/td[2]/text()').extract_first()
        company_item['business_scope'] = icinfo.xpath('.//tr[8]/td[2]/text()').extract_first()
        # yield company_item

        list_href = response.xpath('//a[contains(text(),"上市信息")]/@href').extract_first()
        if list_href:
            ## 爬取上市信息---Done
            list_url = response.urljoin(list_href)
            yield scrapy.Request(list_url, meta={'company_item': company_item,
                                                 'company_key': company_key, 'depth':1}, callback=self.parse_list_info)
        else:
            yield company_item
            # 主要人员
            employees = response.css('#employees').xpath('.//a[@data-event-name="主要人员-点击名字"]')
            num = 0
            executive_key_list = []
            for employee in employees:
                executive_item = ExecutiveItem()
                executive_key = company_key + '_e' + str(num)
                executive_item['_key'] = executive_key
                executive_item['post'] = employee.xpath('../preceding-sibling::td[1]/text()').extract_first()
                executive_item['href'] = employee.xpath('./@href').extract_first()
                executive_item['name'] = employee.xpath('./text()').extract_first()
                yield executive_item
                num = num + 1
                executive_key_list.append(executive_key)
            # 存储公司-高管关系表
            c_e_item = CompanyExecutiveItem()
            c_e_item['company_key'] = company_key
            c_e_item['executive_key'] = executive_key_list
            yield c_e_item

        # 爬取对外投资---Done
        investment_btn = response.xpath('//a[contains(text(),"对外投资")]/../@class').extract_first()
        if investment_btn != 'disable':
            investment_href = response.xpath('//a[contains(text(),"对外投资")]/@href').extract_first()
            investment_url = response.urljoin(investment_href)
            yield scrapy.Request(investment_url, meta={'company_key': company_key, 'depth': 1},
             callback=self.parse_investments)


    # 爬取对外投资
    def parse_investments(self, response):
        company_key = response.meta['company_key']
        num = 0
        investments_key_list = []
        total_page = math.ceil(int(response.css(
            'body > div.container > div > div.col-md-18 > div.tab-content > div.clearfix.margin-t-2x > h4 > span::text').extract_first()) / 10)
        # 第一页
        list = response.css('.app-investment-list .investment-item')
        for li in list:
            investment_key = company_key + '_i' + str(num)
            href = li.css('.col-2 h5 a::attr(href)').extract_first()
            investment_item = InvestmentsItem()
            investment_item['_key'] = investment_key
            investment_item['company_name'] = li.css('.col-2 h5 a::text').extract_first()
            investment_item['href'] = href
            num = num + 1
            investments_key_list.append(investment_key)
            yield investment_item
        if total_page > 1:
            # 其他页
            option = Options()
            # option.add_argument('--headless')
            browser = webdriver.Chrome(options=option)
            browser.get(response.url)
            wait = WebDriverWait(browser, 10)
            # 登录
            if re.search('login', browser.current_url):
                login(wait)
            # 翻页
            for i in range(1, total_page):
                if len(browser.find_elements_by_class_name('modal-backdrop')) == 1:
                    login(wait)
                try:
                    pagination = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'pagination')))
                    browser.execute_script("arguments[0].scrollIntoView(false);", pagination)
                    next = wait.until(EC.presence_of_element_located(
                        (By.XPATH, '//ul[@class="pagination"]//li[@class="active"]/following-sibling::li[1]/a')))
                    next.click()
                    time.sleep(1)
                except TimeoutException:
                    print("Timeout!")
                doc = pq(browser.page_source)
                items = doc('.app-investment-list .investment-item').items()
                for li in items:
                    investment_key = company_key + '_i' + str(num)
                    href = li.find('.h5').children().attr('href')
                    investment_item = InvestmentsItem()
                    investment_item['_key'] = investment_key
                    investment_item['company_name'] = li.find('.h5').text()
                    investment_item['href'] = href
                    num = num + 1
                    investments_key_list.append(investment_key)
                    yield investment_item
        c_i_item = CompanyInvestmentsItem()
        c_i_item['company_key'] = company_key
        c_i_item['investments_key'] = investments_key_list
        yield c_i_item
        # 爬取下一级公司
        ## 数据库操作
        client = MongoClient(self.settings.MONGO_URI)
        db = client[self.settings.MONGO_DB]
        for i in db['InvestmentsItem'].find({"_key": eval("/" + company_key)}):
            if response.meta['depth'] <= self.max_depth:
                yield scrapy.Request(response.urljoin(i['href']),
                                     meta={'depth': response.meta['depth'] + 1}, callback=self.parse)
            else:
                ###################
                company_item = CompanyItem()
                company_item['_key'] = i['_key']
                company_item['company_name'] = i['company_name']
                yield company_item
                ################

    # 爬取上市信息
    def parse_list_info(self, response):
        company_key = response.meta['company_key']

        # 爬取十大股东
        shareholders_key_list = []
        for i in range(10):
            # shareholders_item = ShareholdersItem()
            # shareholders_key = company_key + '_s' + str(i)
            # shareholders_item['_key'] = shareholders_key
            # shareholders_item['name'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]//text()', n=45+i*4).extract_first()
            # shareholders_item['href'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]/a/@href', n=45+i*4).extract_first()
            # shareholders_item['sock_type'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]/text()', n=46+i*4).extract_first()
            # shareholders_item['sock_number'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[4]/text()', n=46+i*4).extract_first()
            # shareholders_item['sock_rate'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]/text()', n=47+i*4).extract_first()
            # shareholders_item['sock_change'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[4]/text()', n=47+i*4).extract_first()
            # shareholders_item['change_rate'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]/text()', n=48+i*4).extract_first()
            # yield shareholders_item
            shareholders_key = company_key + '_s' + str(i)
            href = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]/a/@href', n=45+i*4).extract_first()
            shareholders_key_list.append(shareholders_key)
            # 爬取下一级公司
            if href and response.meta['depth'] < self.max_depth:
                yield scrapy.Request(response.urljoin(href), meta={'depth': response.meta['depth'] + 1, 'company_key': shareholders_key}, callback=self.parse)
            ###################
            else:
                company_item = CompanyItem()
                company_item['_key'] = shareholders_key
                company_item['company_name'] = response.xpath('//*[@id="partners"]/table/tbody/tr[$n]/td[2]//text()', n=45+i*4).extract_first()
                yield company_item
            #################
        # 存储公司-股东关系表
        c_s_item = CompanyShareholdersItem()
        c_s_item['company_key'] = company_key
        c_s_item['shareholders_key'] = shareholders_key_list
        yield c_s_item

        # 高管信息
        names = response.css('#newOTCEmployees table tbody').xpath('.//td[contains(text(),"姓名")]')
        executive_key_list = []
        id = 0
        for name in names:
            executive_info_item = ExecutiveItem()
            executive_key = company_key + '_e' + str(id)
            executive_info_item['_key'] = executive_key
            executive_info_item['name'] = name.xpath('./following-sibling::td/a[1]/text()').extract_first()
            executive_info_item['href'] = name.xpath('./following-sibling::td/a[1]/@href').extract_first()
            executive_info_item['post'] = name.xpath('../following-sibling::tr[1]/td[2]/text()').extract_first()
            executive_info_item['age'] = name.xpath('../following-sibling::tr[1]/td[4]/text()').extract_first()
            executive_info_item['education'] = name.xpath('../following-sibling::tr[2]/td[2]/text()').extract_first()
            executive_info_item['appointment_date'] = name.xpath('../following-sibling::tr[2]/td[4]/text()').extract_first()
            yield executive_info_item
            id = id + 1
            executive_key_list.append(executive_key)
        # 存储公司-高管关系表
        c_e_item = CompanyExecutiveItem()
        c_e_item['company_key'] = company_key
        c_e_item['executive_key'] = executive_key_list
        yield c_e_item

        # 爬取企业概况
        company_item = response.meta['company_item']
        company_item['company_en_name'] = response.xpath('//*[@id="overview"]/table/tbody/tr[1]/td[4]/text()').extract_first()
        company_item['chairman'] = response.xpath('//*[@id="overview"]/table/tbody/tr[2]/td[2]/text()').extract_first()
        company_item['build_date'] = response.xpath('//*[@id="overview"]/table/tbody/tr[4]/td[2]/text()').extract_first()
        company_item['list_date'] = response.xpath('//*[@id="overview"]/table/tbody/tr[4]/td[4]/text()').extract_first()
        company_item['registered_address'] = response.xpath('//*[@id="overview"]/table/tbody/tr[8]/td[2]/text()').extract_first()
        company_item['office_address'] = response.xpath('//*[@id="overview"]/table/tbody/tr[9]/td[2]/text()').extract_first()
        company_item['phone'] = response.xpath('//*[@id="overview"]/table/tbody/tr[10]/td[2]/text()').extract_first()
        company_item['email'] = response.xpath('//*[@id="overview"]/table/tbody/tr[10]/td[4]/text()').extract_first()
        company_item['website'] = response.xpath('//*[@id="overview"]/table/tbody/tr[11]/td[2]/text()').extract_first()
        company_item['fax'] = response.xpath('//*[@id="overview"]/table/tbody/tr[11]/td[4]/text()').extract_first()
        company_item['brief'] = response.xpath('//*[@id="overview"]/table/tbody/tr[12]/td[2]/text()').extract_first()
        yield company_item


def login(wait):
    try:
        username = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'input-flat-user')))
        password = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'input-flat-lock')))
        submit = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-block')))
        username.send_keys('13631433117')
        password.send_keys('123456')
        submit.click()
        time.sleep(1)
        # print('login function is called!')
    except TimeoutError:
        print('Timeout!')