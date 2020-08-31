import configparser
import json
import logging
import os
import socket
import threading
import traceback
import uuid
import xml.etree.ElementTree as ET
from json import dumps
from os import unlink

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from httplib2 import Http
from werkzeug.utils import secure_filename

from .args import parse_options

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()
logger.addHandler(logging.FileHandler('test.log', 'a'))
print = logger.info

app = Flask(__name__, template_folder='templates')

mysql = MySQL(app)

UPLOAD_FOLDER = ''
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/redirect')
def redirect_url():
    return render_template('redirect.html')


@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')


@app.route('/automation-home', methods=['GET'])
def automation_home():
    cursor = mysql.connection.cursor()
    use_db(cursor, "pytesthistoric")
    cursor.execute("select * from TB_PROJECT;")
    data = cursor.fetchall()
    return render_template('automation-home.html', data=data)


@app.route('/sa-home', methods=['GET'])
def sa_home():
    cursor = mysql.connection.cursor()
    use_db(cursor, "pytesthistoric")
    cursor.execute("select * from SA_PROJECT;")
    data = cursor.fetchall()
    return render_template('sa-home.html', data=data)


@app.route('/<db>/deldbconf', methods=['GET'])
def delete_db_conf(db):
    return render_template('deldbconf.html', db_name=db)


@app.route('/<db>/sa-deldbconf', methods=['GET'])
def sa_delete_db_conf(db):
    return render_template('sa-deldbconf.html', db_name=db)


@app.route('/<db>/delete', methods=['GET'])
def delete_db(db):
    cursor = mysql.connection.cursor()
    cursor.execute("DROP DATABASE %s;" % db)
    # use_db(cursor, "pytesthistoric")
    cursor.execute("DELETE FROM pytesthistoric.TB_PROJECT WHERE Project_Name='%s';" % db)
    mysql.connection.commit()
    return redirect(url_for('home'))


@app.route('/<db>/sa-delete', methods=['GET'])
def sa_delete_db(db):
    cursor = mysql.connection.cursor()
    cursor.execute("DROP DATABASE %s;" % db)
    # use_db(cursor, "pytesthistoric")
    cursor.execute("DELETE FROM pytesthistoric.SA_PROJECT WHERE Project_Name='%s';" % db)
    mysql.connection.commit()
    return redirect(url_for('sa_home'))


@app.route('/newdb', methods=['GET', 'POST'])
def add_db():
    if request.method == "POST":
        db_name = request.form['dbname']
        db_desc = request.form['dbdesc']
        db_image = request.form['dbimage']
        db_webhook = request.form['dbwebhook']
        cursor = mysql.connection.cursor()
        try:
            # create new database for project
            cursor.execute("Create DATABASE %s;" % db_name)
            # update created database info in pytesthistoric.TB_PROJECT table
            cursor.execute(
                "INSERT INTO pytesthistoric.TB_PROJECT ( Project_Id, Project_Name, Project_Desc, Project_Image, Created_Date, Last_Updated, Total_Executions, Recent_Pass_Perc, Overall_Pass_Perc, Project_Webhook) VALUES (0, '%s', '%s', '%s', NOW(), NOW(), 0, 0, 0, '%s');" % (
                    db_name, db_desc, db_image, db_webhook))
            # create tables in created database
            use_db(cursor, db_name)
            cursor.execute(
                "Create table TB_EXECUTION ( Execution_Id INT NOT NULL auto_increment primary key, Execution_Date DATETIME, Execution_Desc TEXT, Execution_Executed INT, Execution_Pass INT, Execution_Fail INT, Execution_Skip INT, Execution_XPass INT, Execution_XFail INT, Execution_Error INT, Execution_Time FLOAT, Execution_Version TEXT);")
            cursor.execute(
                "Create table TB_SUITE ( Suite_Id INT NOT NULL auto_increment primary key, Execution_Id INT, Suite_Name TEXT, Suite_Executed INT, Suite_Pass INT, Suite_Fail INT, Suite_Skip INT, Suite_XPass INT, Suite_XFail INT, Suite_Error INT);")
            cursor.execute(
                "Create table TB_TEST ( Test_Id INT NOT NULL auto_increment primary key, Execution_Id INT, Test_Name TEXT, Test_Status CHAR(5), Test_Time FLOAT, Test_Error TEXT, Test_Comment TEXT);")
            mysql.connection.commit()
        except Exception as e:
            print(traceback.format_exc())

        finally:
            return redirect(url_for('home'))
    else:
        return render_template('newdb.html')


@app.route('/sa-newdb', methods=['GET', 'POST'])
def sa_add_db():
    if request.method == "POST":
        db_name = request.form['dbname']
        db_desc = request.form['dbdesc']
        db_image = request.form['dbimage']
        db_webhook = request.form['dbwebhook']
        cursor = mysql.connection.cursor()
        try:
            # create new database for project
            cursor.execute("Create DATABASE %s;" % db_name)
            # update created database info in pytesthistoric.SA_PROJECT table
            cursor.execute(
                "INSERT INTO pytesthistoric.SA_PROJECT ( Project_Id, Project_Name, Project_Desc, Project_Image, Created_Date, Last_Updated, Total_Executions, Project_Webhook) VALUES (0, '%s', '%s', '%s', NOW(), NOW(), 0, '%s');" % (
                    db_name, db_desc, db_image, db_webhook))
            # create tables in created database
            use_db(cursor, db_name)
            print("static_analysis")
            cursor.execute(
                "Create table SA_EXECUTION ( Execution_Id INT NOT NULL auto_increment primary key, Execution_Date DATETIME, Component_Version TEXT, Build_Version TEXT, Pipeline_Link TEXT, Artifact_Link TEXT, Priority_High INT, Priority_Low INT, Priority_Medium INT, Git_Commit TEXT, Git_Url TEXT, Project_Dir TEXT, Commits_After_Tag INT, Git_Branch TEXT, Compilation_Error TEXT, Git_Commit_Message TEXT);")
            cursor.execute(
                "Create table SA_DEFECT ( Defect_Id INT NOT NULL auto_increment primary key, Execution_Id INT, Defect_Category TEXT, Defect_Check TEXT, Defect_Priority TEXT, Defect_File_Path TEXT, Defect_Function TEXT, Defect_Begin_Line TEXT, Defect_End_Line TEXT, Defect_Column TEXT, Defect_Comment TEXT, Defect_Link TEXT, Defect_Fingerprint TEXT, Defect_Severity TEXT, Defect_Message TEXT, Defect_Summary TEXT, Defect_Explanation TEXT);")
            mysql.connection.commit()
        except Exception as e:
            print(traceback.format_exc())

        finally:
            return redirect(url_for('sa_home'))
    else:
        return render_template('sa-newdb.html')


@app.route('/<db_name>/editdb', methods=['GET', 'POST'])
def edit_db(db_name):
    if request.method == "POST":
        db_desc = request.form['dbdesc']
        db_image = request.form['dbimage']
        db_webhook = request.form['dbwebhook']
        cursor = mysql.connection.cursor()

        try:
            # update created database info in pytesthistoric.TB_PROJECT table
            if db_desc:
                cursor.execute(
                    "UPDATE pytesthistoric.TB_PROJECT SET Project_Desc = '%s' WHERE Project_Name = '%s';" % (
                        db_desc, db_name))
            if db_image:
                cursor.execute(
                    "UPDATE pytesthistoric.TB_PROJECT SET Project_Image ='%s' WHERE Project_Name = '%s';" % (
                        db_image, db_name))
            if db_webhook:
                cursor.execute(
                    "UPDATE pytesthistoric.TB_PROJECT SET Project_Webhook='%s' WHERE Project_Name = '%s';" % (
                        db_webhook, db_name))
            mysql.connection.commit()
        except Exception as e:
            print(str(e))

        finally:
            return redirect(url_for('home'))
    else:
        return render_template('editdb.html', db_name=db_name)


@app.route('/<db_name>/sa-editdb', methods=['GET', 'POST'])
def sa_edit_db(db_name):
    if request.method == "POST":
        db_desc = request.form['dbdesc']
        db_image = request.form['dbimage']
        db_webhook = request.form['dbwebhook']
        cursor = mysql.connection.cursor()

        try:
            # update created database info in pytesthistoric.TB_PROJECT table
            if db_desc:
                cursor.execute(
                    "UPDATE pytesthistoric.SA_PROJECT SET Project_Desc = '%s' WHERE Project_Name = '%s';" % (
                        db_desc, db_name))
            if db_image:
                cursor.execute(
                    "UPDATE pytesthistoric.SA_PROJECT SET Project_Image ='%s' WHERE Project_Name = '%s';" % (
                        db_image, db_name))
            if db_webhook:
                cursor.execute(
                    "UPDATE pytesthistoric.SA_PROJECT SET Project_Webhook='%s' WHERE Project_Name = '%s';" % (
                        db_webhook, db_name))
            mysql.connection.commit()
        except Exception as e:
            print(str(e))

        finally:
            return redirect(url_for('sa_home'))
    else:
        return render_template('sa-editdb.html', db_name=db_name)


@app.route('/<db>/dashboard', methods=['GET'])
def dashboard(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)

    cursor.execute("SELECT COUNT(Execution_Id) from TB_EXECUTION;")
    results_data = cursor.fetchall()
    cursor.execute("SELECT COUNT(Suite_Id) from TB_SUITE;")
    suite_results_data = cursor.fetchall()
    cursor.execute("SELECT COUNT(Test_Id) from TB_TEST;")
    test_results_data = cursor.fetchall()

    if results_data[0][0] > 0 and suite_results_data[0][0] > 0 and test_results_data[0][0] > 0:

        cursor.execute(
            "SELECT Execution_Pass, Execution_Fail, Execution_XPass, Execution_XFail, Execution_Executed, Round(Execution_Time/60,2) from TB_EXECUTION order by Execution_Id desc LIMIT 1;")
        last_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT SUM(Execution_Pass), SUM(Execution_Fail), SUM(Execution_XPass), SUM(Execution_XFail), SUM(Execution_Executed), COUNT(Execution_Id) from (SELECT Execution_Pass, Execution_Fail, Execution_XPass, Execution_XFail, Execution_Executed, Execution_Id from TB_EXECUTION order by Execution_Id desc LIMIT 10) AS T;")
        last_ten_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT SUM(Execution_Pass), SUM(Execution_Fail), SUM(Execution_XPass), SUM(Execution_XFail), SUM(Execution_Executed), COUNT(Execution_Id) from TB_EXECUTION order by Execution_Id desc;")
        over_all_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT Execution_Desc, Execution_Pass, Execution_Fail, Execution_XPass, Execution_XFail, Execution_Time from TB_EXECUTION order by Execution_Id desc LIMIT 10;")
        last_ten_data = cursor.fetchall()

        cursor.execute(
            "select 'DUMMY', ROUND(MIN(execution_pass),2), ROUND(AVG(execution_pass),2), ROUND(MAX(execution_pass),2) from TB_EXECUTION order by execution_id desc;")
        execution_pass_data = cursor.fetchall()

        cursor.execute(
            "select 'DUMMY', ROUND(MIN(execution_fail),2), ROUND(AVG(execution_fail),2), ROUND(MAX(execution_fail),2) from TB_EXECUTION order by execution_id desc;")
        execution_fail_data = cursor.fetchall()

        cursor.execute(
            "select 'DUMMY', ROUND(MIN(execution_time)/60,2), ROUND(AVG(execution_time)/60,2), ROUND(MAX(execution_time)/60,2) from TB_EXECUTION order by execution_id desc;")
        execution_time_data = cursor.fetchall()

        return render_template('dashboard.html', last_ten_data=last_ten_data,
                               last_exe_pie_data=last_exe_pie_data,
                               last_ten_exe_pie_data=last_ten_exe_pie_data,
                               over_all_exe_pie_data=over_all_exe_pie_data,
                               execution_pass_data=execution_pass_data,
                               execution_fail_data=execution_fail_data,
                               execution_time_data=execution_time_data, db_name=db)

    else:
        return redirect(url_for('redirect_url'))


@app.route('/<db>/sa-dashboard', methods=['GET'])
def sa_dashboard(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)

    cursor.execute("SELECT COUNT(Execution_Id) from SA_EXECUTION;")
    results_data = cursor.fetchall()
    cursor.execute("SELECT COUNT(Defect_Id) from SA_DEFECT;")
    defects_data = cursor.fetchall()

    if results_data[0][0] > 0 and defects_data[0][0] > 0:

        cursor.execute(
            "SELECT Priority_High, Priority_Low, Priority_Medium from SA_EXECUTION order by Execution_Id desc LIMIT 1;")
        last_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT SUM(Priority_High), SUM(Priority_Low), SUM(Priority_Medium), COUNT(Execution_Id) from (SELECT Priority_High, Priority_Low, Priority_Medium, Execution_Id from SA_EXECUTION order by Execution_Id desc LIMIT 10) as T;")
        last_ten_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT SUM(Priority_High), SUM(Priority_Low), SUM(Priority_Medium), COUNT(Execution_Id) from SA_EXECUTION order by Execution_Id desc;")
        over_all_exe_pie_data = cursor.fetchall()

        cursor.execute(
            "SELECT Component_Version, Priority_High, Priority_Low, Priority_Medium from SA_EXECUTION order by Execution_Id desc LIMIT 10;")
        last_ten_data = cursor.fetchall()

        cursor.execute(
            "SELECT ROUND(MIN(Priority_High),2), ROUND(AVG(Priority_High),2), ROUND(MAX(Priority_High),2) from SA_EXECUTION order by Execution_Id desc;")
        high_priority_data = cursor.fetchall()

        cursor.execute(
            "SELECT ROUND(MIN(Priority_Low),2), ROUND(AVG(Priority_Low),2), ROUND(MAX(Priority_Low),2) from SA_EXECUTION order by Execution_Id desc;")
        low_priority_data = cursor.fetchall()

        cursor.execute(
            "SELECT ROUND(MIN(Priority_Medium),2), ROUND(AVG(Priority_Medium),2), ROUND(MAX(Priority_Medium),2) from SA_EXECUTION order by Execution_Id desc;")
        medium_priority_data = cursor.fetchall()

        return render_template('sa-dashboard.html', last_ten_data=last_ten_data,
                               last_exe_pie_data=last_exe_pie_data,
                               last_ten_exe_pie_data=last_ten_exe_pie_data,
                               over_all_exe_pie_data=over_all_exe_pie_data,
                               high_priority_data=high_priority_data,
                               low_priority_data=low_priority_data,
                               medium_priority_data=medium_priority_data, db_name=db)

    else:
        return redirect(url_for('redirect_url'))


@app.route('/<db>/ehistoric', methods=['GET'])
def ehistoric(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    cursor.execute("SELECT * from TB_EXECUTION order by Execution_Id desc LIMIT 500;")
    data = cursor.fetchall()
    return render_template('ehistoric.html', data=data, db_name=db)


@app.route('/<db>/sa-ehistoric', methods=['GET'])
def sa_ehistoric(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    cursor.execute("SELECT * from SA_EXECUTION order by Execution_Id desc LIMIT 500;")
    data = cursor.fetchall()
    return render_template('sa-ehistoric.html', data=data, db_name=db)


@app.route('/<db>/deleconf/<eid>', methods=['GET'])
def delete_eid_conf(db, eid):
    return render_template('deleconf.html', db_name=db, eid=eid)


@app.route('/<db>/sa-deleconf/<eid>', methods=['GET'])
def sa_delete_eid_conf(db, eid):
    return render_template('sa-deleconf.html', db_name=db, eid=eid)


@app.route('/<db>/edelete/<eid>', methods=['GET'])
def delete_eid(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    # remove execution from tables: execution, suite, test
    cursor.execute("DELETE FROM TB_EXECUTION WHERE Execution_Id='%s';" % eid)
    cursor.execute("DELETE FROM TB_SUITE WHERE Execution_Id='%s';" % eid)
    cursor.execute("DELETE FROM TB_TEST WHERE Execution_Id='%s';" % eid)
    # get latest execution info
    cursor.execute("SELECT Execution_Pass, Execution_Executed from TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
    data = cursor.fetchall()
    # get no. of executions
    cursor.execute("SELECT COUNT(*) from TB_EXECUTION;")
    exe_data = cursor.fetchall()

    try:
        if data[0][0] > 0:
            recent_pass_perf = float("{0:.2f}".format((data[0][0] / data[0][1] * 100)))
        else:
            recent_pass_perf = 0
    except:
        recent_pass_perf = 0

    # update pytesthistoric project
    cursor.execute(
        "UPDATE pytesthistoric.TB_PROJECT SET Total_Executions=%s, Last_Updated=now(), Recent_Pass_Perc=%s WHERE Project_Name='%s';" % (
            int(exe_data[0][0]), recent_pass_perf, db))
    # commit changes
    mysql.connection.commit()
    return redirect(url_for('ehistoric', db=db))


@app.route('/<db>/sa-edelete/<eid>', methods=['GET'])
def sa_delete_eid(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    # remove execution from tables: execution, suite, test
    cursor.execute("DELETE FROM SA_EXECUTION WHERE Execution_Id='%s';" % eid)
    cursor.execute("DELETE FROM SA_DEFECT WHERE Execution_Id='%s';" % eid)
    # get no. of executions
    cursor.execute("SELECT COUNT(*) from SA_EXECUTION;")
    exe_data = cursor.fetchall()

    # update pytesthistoric project
    cursor.execute(
        "UPDATE pytesthistoric.SA_PROJECT SET Total_Executions=%s, Last_Updated=now() WHERE Project_Name='%s';" % (
            int(exe_data[0][0]), db))
    # commit changes
    mysql.connection.commit()
    return redirect(url_for('sa_ehistoric', db=db))


@app.route('/<db>/tmetrics', methods=['GET', 'POST'])
def tmetrics(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    if request.method == "POST":
        textField = request.form['textField']
        rowField = request.form['rowField']
        cursor.execute("Update TB_TEST SET Test_Comment='%s' WHERE Test_Id=%s;" % (str(textField), str(rowField)))
        mysql.connection.commit()

    # Get last row execution ID
    cursor.execute("SELECT Execution_Id from TB_EXECUTION order by Execution_Id desc LIMIT 1;")
    data = cursor.fetchone()
    # Get testcase results of execution id (typically last executed)
    cursor.execute("SELECT * from TB_TEST WHERE Execution_Id=%s;" % data)
    data = cursor.fetchall()
    return render_template('tmetrics.html', data=data, db_name=db)


@app.route('/<db>/sa-dmetrics', methods=['GET', 'POST'])
def sa_dmetrics(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    if request.method == "POST":
        textField = request.form['textField']
        rowField = request.form['rowField']
        cursor.execute("Update SA_DEFECT SET Defect_Comment='%s' WHERE Defect_Id=%s;" % (str(textField), str(rowField)))
        mysql.connection.commit()

    # Get last row execution ID
    cursor.execute("SELECT Execution_Id from SA_EXECUTION order by Execution_Id desc LIMIT 1;")
    data = cursor.fetchone()
    # Get testcase results of execution id (typically last executed)
    cursor.execute("SELECT * from SA_DEFECT WHERE Execution_Id=%s;" % data)
    data = cursor.fetchall()
    return render_template('sa-dmetrics.html', data=data, db_name=db)


@app.route('/<db>/metrics/<eid>', methods=['GET'])
def metrics(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    # Get testcase results of execution id
    cursor.execute("SELECT * from TB_TEST WHERE Execution_Id=%s;" % eid)
    test_data = cursor.fetchall()
    # get suite results of execution id
    cursor.execute("SELECT * from TB_SUITE WHERE Execution_Id=%s;" % eid)
    suite_data = cursor.fetchall()
    # get project image
    cursor.execute("SELECT Project_Image from pytesthistoric.TB_PROJECT WHERE Project_Name='%s';" % db)
    project_image = cursor.fetchall()
    # get execution info
    cursor.execute("SELECT * from TB_EXECUTION WHERE Execution_Id=%s;" % eid)
    exe_data = cursor.fetchall()
    return render_template('metrics.html', suite_data=suite_data, test_data=test_data,
                           project_image=project_image[0][0], exe_data=exe_data)


@app.route('/<db>/sa-metrics/<eid>', methods=['GET'])
def sa_metrics(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    # Get testcase results of execution id
    cursor.execute("SELECT * from SA_DEFECT WHERE Execution_Id=%s;" % eid)
    test_data = cursor.fetchall()
    # get project image
    cursor.execute("SELECT Project_Image from pytesthistoric.SA_PROJECT WHERE Project_Name='%s';" % db)
    project_image = cursor.fetchall()
    # get execution info
    cursor.execute("SELECT * from SA_EXECUTION WHERE Execution_Id=%s;" % eid)
    exe_data = cursor.fetchall()
    # get defect check info
    cursor.execute(f"SELECT COUNT(Defect_Id), Defect_Check from SA_DEFECT WHERE Execution_Id = {eid} "
                   f"GROUP BY Defect_Check ORDER BY COUNT(Defect_Id) DESC;")
    defect_check_data = cursor.fetchall()
    # get defect category info
    cursor.execute(f"SELECT COUNT(Defect_Id), Defect_Category from SA_DEFECT WHERE Execution_Id = {eid} "
                   f"GROUP BY Defect_Category ORDER BY COUNT(Defect_Id) DESC;")
    defect_category_data = cursor.fetchall()
    graph_data = {"check": defect_check_data, "category": defect_category_data}
    graph_data = json.dumps(graph_data)
    return render_template('sa-metrics.html', test_data=test_data,
                           project_image=project_image[0][0], exe_data=exe_data,
                           graph_data=graph_data, db=db)


@app.route('/<db>/tmetrics/<eid>', methods=['GET', 'POST'])
def eid_tmetrics(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    if request.method == "POST":
        textField = request.form['textField']
        rowField = request.form['rowField']
        cursor.execute("Update TB_TEST SET Test_Comment='%s' WHERE Test_Id=%s;" % (str(textField), str(rowField)))
        mysql.connection.commit()

    # Get testcase results of execution id (typically last executed)
    cursor.execute("SELECT * from TB_TEST WHERE Execution_Id=%s;" % eid)
    data = cursor.fetchall()
    return render_template('eidtmetrics.html', data=data, db_name=db)


@app.route('/<db>/sa-dmetrics/<eid>', methods=['GET', 'POST'])
def sa_eid_tmetrics(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    if request.method == "POST":
        textField = request.form['textField']
        rowField = request.form['rowField']
        cursor.execute("Update SA_DEFECT SET Defect_Comment='%s' WHERE Defect_Id=%s;" % (str(textField), str(rowField)))
        mysql.connection.commit()

    # Get testcase results of execution id (typically last executed)
    cursor.execute("SELECT * from SA_DEFECT WHERE Execution_Id=%s;" % eid)
    data = cursor.fetchall()
    return render_template('sa-eiddmetrics.html', data=data, db_name=db)


@app.route('/<db>/failures/<eid>', methods=['GET', 'POST'])
def eid_failures(db, eid):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    if request.method == "POST":
        textField = request.form['textField']
        rowField = request.form['rowField']
        cursor.execute("Update TB_TEST SET Test_Comment='%s' WHERE Test_Id=%s;" % (str(textField), str(rowField)))
        mysql.connection.commit()

    # Get testcase results of execution id (typically last executed)
    cursor.execute("SELECT * from TB_TEST WHERE Execution_Id=%s and Test_Status='FAIL';" % eid)
    data = cursor.fetchall()
    return render_template('failures.html', data=data, db_name=db)


@app.route('/<db>/search', methods=['GET', 'POST'])
def search(db):
    if request.method == "POST":
        search = request.form['search']
        cursor = mysql.connection.cursor()
        use_db(cursor, db)
        cursor.execute(
            "SELECT * from TB_TEST WHERE Test_Name LIKE '%{name}%' OR Test_Status LIKE '%{name}%' OR Execution_Id LIKE '%{name}%' ORDER BY Execution_Id DESC LIMIT 10000;".format(
                name=search))
        data = cursor.fetchall()
        return render_template('search.html', data=data, db_name=db)
    else:
        return render_template('search.html', db_name=db)


@app.route('/<db>/flaky', methods=['GET'])
def flaky(db):
    cursor = mysql.connection.cursor()
    use_db(cursor, db)
    cursor.execute(
        "SELECT Execution_Id from ( SELECT Execution_Id from TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 5 ) as tmp ORDER BY Execution_Id ASC LIMIT 1;")
    last_five = cursor.fetchall()
    cursor.execute("SELECT Execution_Id from TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 5;")
    last_five_ids = cursor.fetchall()
    sql_query = "SELECT Execution_Id, Test_Name, Test_Status from TB_TEST WHERE Execution_Id >= %s ORDER BY Execution_Id DESC;" % (
        str(last_five[0][0]))

    cursor.execute(sql_query)
    data = cursor.fetchall()
    # print("==== Before Sorted Data ===")
    # print(data)
    sorted_data = sort_tests(data)
    # print("==== After Sorted Data ===")
    # print(sorted_data)
    return render_template('flaky.html', data=sorted_data, db_name=db, builds=last_five_ids)


@app.route('/<db>/compare', methods=['GET', 'POST'])
def compare(db):
    if request.method == "POST":
        eid_one = request.form['eid_one']
        eid_two = request.form['eid_two']
        cursor = mysql.connection.cursor()
        use_db(cursor, db)
        # fetch first eid tets results
        cursor.execute(
            "SELECT Execution_Id, Test_Name, Test_Status, Test_Time, Test_Error from TB_TEST WHERE Execution_Id=%s;" % eid_one)
        first_data = cursor.fetchall()
        # fetch second eid test results
        cursor.execute(
            "SELECT Execution_Id, Test_Name, Test_Status, Test_Time, Test_Error from TB_TEST WHERE Execution_Id=%s;" % eid_two)
        second_data = cursor.fetchall()
        # combine both tuples
        data = first_data + second_data
        sorted_data = sort_tests(data)
        return render_template('compare.html', data=sorted_data, db_name=db, fb=eid_one, sb=eid_two)
    else:
        return render_template('compare.html', db_name=db)


@app.route('/<db>/sa-compare', methods=['GET', 'POST'])
def sa_compare(db):
    if request.method == "POST" or ('eid_one' in request.args and 'eid_two' in request.args):
        eid_one = request.form['eid_one'] if 'eid_one' in request.form else request.args['eid_one']
        eid_two = request.form['eid_two'] if 'eid_two' in request.form else request.args['eid_two']
        cursor = mysql.connection.cursor()
        use_db(cursor, db)
        result, data = compare_defects(eid_one, eid_two, cursor)
        cursor.execute(f"SELECT Component_Version from SA_EXECUTION WHERE Execution_Id={eid_one}")
        first_comp = (cursor.fetchone()[0], eid_one)
        cursor.execute(f"SELECT Component_Version from SA_EXECUTION WHERE Execution_Id={eid_two}")
        sec_comp = (cursor.fetchone()[0], eid_two)
        return render_template('sa-compare.html', data=data, db_name=db, first_comp=first_comp, sec_comp=sec_comp)
    else:
        return render_template('sa-compare.html', db_name=db)


def compare_defects(eid_one, eid_two, cursor):
    cursor.execute(f"SELECT * FROM SA_DEFECT WHERE Execution_Id={eid_one} AND Defect_Fingerprint NOT IN "
                   f"(SELECT Defect_Fingerprint FROM  SA_DEFECT WHERE Execution_Id={eid_two});")
    data = cursor.fetchall()
    if data:
        return False, data
    else:
        return True, data


def parse_sa_report(report_file, tool, cursor, eid, commit_url, project_dir, submodule_file, submodule_commits):
    defect_count = 0
    config = configparser.ConfigParser()
    temp_count = {"high": [], "low": [], "medium": []}
    if not submodule_commits.isspace() and submodule_commits:
        filename = secure_filename(submodule_file.filename)
        unique_filename = str(uuid.uuid4())
        filename += f"_{unique_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        submodule_file.save(filepath)
        config.read(filepath)
        unlink(filepath)
        for line in submodule_commits.split("\n"):
            path = line.split()[1]
            for section in config.sections():
                if config[section]["path"] == path:
                    config[section]["commit"] = line.split()[0][:8]
                    break
    if tool == "polyspace":
        df = pd.read_csv(report_file, sep='\t', header=[0])
        for i in range(df.shape[0]):
            defect_link = str()
            file_path = df['File'][i].replace(f"{project_dir}/", '')
            for section in config.sections():
                if file_path.startswith(config[section]["path"]):
                    defect_link = f"{commit_url.split('-')[0]}/{config[section]['url'].replace('.git', '')}/-/blob/{config[section]['commit']}{file_path.replace(config[section]['path'], '')} "
                    # print(defect_link)
                    break
            if not defect_link:
                defect_link = f"{commit_url}{df['File'][i].replace(project_dir, '')}"
            cursor.execute(
                f"INSERT INTO SA_DEFECT (Execution_Id, Defect_Category, Defect_Check, Defect_Priority, Defect_File_Path, Defect_Function, Defect_Link, Defect_Fingerprint)"
                f" VALUES ({eid}, '{df['Group'][i]}', '{df['Check'][i]}', '{df['Information'][i].replace('Impact: ', '')}','{df['File'][i]}', '{df['Function'][i]}', '{defect_link}',  '{df['Key'][i]}');")
            defect_count += 1
        # Update priority counts
        for priority in temp_count:
            cursor.execute(
                f"SELECT COUNT(Defect_Id) FROM SA_DEFECT WHERE Defect_Priority = '{priority}'  AND  Execution_id = {eid};")
            count = cursor.fetchall()
            temp_count[priority] = count[0][0]

    elif tool == "android-lint":
        root = ET.parse(report_file).getroot()
        for issue in root.findall('issue'):
            defect_link = str()
            for location in issue.findall('location'):
                actual_file_path = location.get('file')
                file_path = actual_file_path.replace(f"{project_dir}/", '')
                defect_line = location.get('line')
                defect_column = location.get('defect_column')
            for section in config.sections():
                if file_path.startswith(config[section]["path"]):
                    defect_link = f"{commit_url.split('-')[0]}/{config[section]['url'].replace('.git', '')}/-/blob/{config[section]['commit']}{file_path.replace(config[section]['path'], '')} "
                    # print(defect_link)
                    break
            if not defect_link:
                defect_link = f"{commit_url}{location.get('file').replace(project_dir, '')}"
            if defect_line:
                defect_link += f"#L{defect_line}"
            summary = issue.get("summary").replace("'", "`")
            message = issue.get('message').replace("'", "`")
            cmd = f"INSERT INTO SA_DEFECT (Execution_Id, Defect_Category, Defect_Check, Defect_Priority, Defect_File_Path, Defect_Function, Defect_Link, Defect_Fingerprint, Defect_Begin_Line, Defect_Column, Defect_Severity, Defect_Message, Defect_Summary)" \
                  f" VALUES ({eid}, '{issue.get('category')}', '{issue.get('id')}', '{issue.get('priority')}','{actual_file_path}', 'NA', '{defect_link}',  '{id}-{file_path}-{defect_line}-{defect_column}', '{defect_line}', '{defect_column}', '{issue.get('severity')}', '{message}', '{summary}');"
            # print(cmd)
            cursor.execute(cmd)
            defect_count += 1
        # Update priority counts
        priority_distribution = {"low": (1, 3), "medium": (4, 7), "high": (8, 10)}
        for priority in temp_count:
            cursor.execute(
                f"SELECT COUNT(Defect_Id) FROM SA_DEFECT WHERE  Defect_Priority BETWEEN {priority_distribution[priority][0]} AND {priority_distribution[priority][1]} AND  Execution_id = {eid};")
            count = cursor.fetchall()
            temp_count[priority] = count[0][0]

    elif tool == "code-quality":
        defects = json.load(report_file)
        for defect in defects:
            defect_link = str()
            file_path = defect['location']['path']
            defect_line_start = defect['location']['lines']['begin']
            defect_line_end = defect['location']['lines']['end']
            defect_description = defect.get('description').replace("'", "`")
            for section in config.sections():
                if file_path.startswith(config[section]["path"]):
                    defect_link = f"{commit_url.split('-')[0]}/{config[section]['url'].replace('.git', '')}/-/blob/{config[section]['commit']}{file_path.replace(config[section]['path'], '')} "
                    # print(defect_link)
                    break
            if not defect_link:
                defect_link = f"{commit_url}/{file_path}"
            if defect_line_start:
                defect_link += f"#L{defect_line_start}"
            cmd = f"INSERT INTO SA_DEFECT (Execution_Id, Defect_Category, Defect_Check, Defect_File_Path, Defect_Link, Defect_Fingerprint, Defect_Begin_Line, Defect_End_Line, Defect_Severity, Defect_Message)" \
                  f" VALUES ({eid}, '{defect['categories'][0]}', '{defect['check_name']}','{file_path}', '{defect_link}', '{defect['fingerprint']}', '{defect_line_start}', '{defect_line_end}', '{defect['severity']}', '{defect_description}');"
            print(cmd)
            cursor.execute(cmd)
            defect_count += 1
        # Update priority counts
        priority_distribution = {"low": "('minor')", "medium": "('major')", "high": "('critical')"}
        for priority in temp_count:
            cmd = f"SELECT COUNT(Defect_Id) FROM SA_DEFECT WHERE  Defect_Severity IN {priority_distribution[priority]} AND Execution_id = {eid};"
            print(cmd)
            cursor.execute(cmd)
            count = cursor.fetchall()
            temp_count[priority] = count[0][0]

    command = f"UPDATE SA_EXECUTION SET Priority_High = {temp_count['high']}, Priority_Low = {temp_count['low']}, " \
              f"Priority_Medium = {temp_count['medium']} WHERE Execution_Id = {eid};"
    print(command)
    cursor.execute(command)
    return defect_count


@app.route('/static', methods=['POST'])
def static_report():
    print(request.form)
    print(request.files)
    submodule_file, submodule_commits = None, None
    compilation_error, commit_msg = 0, None
    try:
        if request.method == 'POST':
            file = request.files['file']
            component = request.form['component']
            component_version = request.form['component-version']
            build_version = request.form['build-version']
            artifact_link = request.form['artifact-link']
            pipeline_link = request.form['pipeline-link']
            commit_id = request.form['commit-id']
            repo_link = request.form['repo-link']
            project_dir = request.form['project-dir']
            commits_after_tag = request.form['commits-after-tag']
            submodule_commits = request.form['submodule-commits']
            if not submodule_commits.isspace() and submodule_commits:
                submodule_file = request.files['submodule']
            git_branch = request.form['git-branch']
            if 'compilation-error' in request.form:
                compilation_error = request.form['compilation-error']
            if 'commit-msg' in request.form:
                commit_msg = request.form['commit-msg']

            if not component_version.isspace() and component_version:
                component_version = f"{component_version}-{git_branch}-{commit_id}" if int(
                    commits_after_tag) > 0 else component_version
            else:
                component_version = "NA"

            tool = request.form['tool']
            cursor = mysql.connection.cursor()
            use_db(cursor, component)
            cmd = f"INSERT INTO SA_EXECUTION (Execution_Date, Component_Version, Pipeline_Link, Artifact_Link, Build_Version, Git_Commit, Git_Url, Project_Dir, Commits_After_Tag, Git_Branch, Compilation_Error, Git_Commit_Message) " \
                  f"VALUES (NOW(), '{component_version}', '{pipeline_link}', '{artifact_link}', '{build_version}', '{commit_id}', '{repo_link}', '{project_dir}', {int(commits_after_tag)}, '{git_branch}', '{compilation_error}', '{commit_msg}');"
            cursor.execute(cmd)
            commit_url = f"{repo_link}/-/blob/{commit_id}"
            mysql.connection.commit()
            cursor.execute(
                "SELECT Execution_Id FROM SA_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
            rows = cursor.fetchone()
            eid = rows[0]
            defect_count = parse_sa_report(file, tool, cursor, eid, commit_url, project_dir, submodule_file,
                                           submodule_commits)
            cursor.execute(
                f"UPDATE pytesthistoric.SA_PROJECT SET Total_Executions=Total_Executions+1 WHERE Project_Name='{component}';")
            mysql.connection.commit()
            cursor.execute(
                f'SELECT Execution_Id FROM SA_EXECUTION WHERE Git_Branch="{git_branch}" AND  Git_Commit<>"{commit_id}" ORDER BY Execution_Id DESC LIMIT 1;')
            prev_eid = cursor.fetchone()

            ip_addr = get_ip()

            webhook = get_webhook(cursor, component)

            if prev_eid:
                prev_eid = prev_eid[0]
                cursor.execute(
                    f"SELECT SUM(Priority_High + Priority_Low + Priority_Medium), Component_Version, Git_Commit FROM SA_EXECUTION WHERE Execution_Id = {prev_eid};")
                temp = cursor.fetchone()
                result, data = compare_defects(eid, prev_eid, cursor)
                prev_count = temp[0]
                prev_version = temp[1]
                prev_commit = temp[2]

                if not result:

                    response = {
                        "Result": "FAIL",
                        "Details": f"Component: {component} \n Branch: {git_branch} \n Commit message: {commit_msg} \n No. of files failed to compile: {compilation_error} \n New defects found - http://{ip_addr}:5000{url_for('sa_compare', db=component, eid_one=eid, eid_two=prev_eid)} \n "
                                   f"Current build: {component_version.split('-')[0]} (Commit-{commit_id}) - Defects: {defect_count} \n "
                                   f"Previous build: {prev_version.split('-')[0]} (Commit-{prev_commit}) - Defects: {prev_count} \n "
                                   f"Dashboard Link: http://{ip_addr}:5000{url_for('sa_metrics', db=component, eid=eid)}"}
                else:
                    response = {
                        "Result": "PASS",
                        "Details": f"Component: {component} \n Branch: {git_branch} \n Commit message: {commit_msg} \n No. of files failed to compile:  {compilation_error} \n Current build: {component_version.split('-')[0]} (Commit-{commit_id}) - Defects: {defect_count} \n "
                                   f"Previous build: {prev_version.split('-')[0]} (Commit-{prev_commit}) - Defects: {prev_count} \n "
                                   f"Dashboard Link: http://{ip_addr}:5000{url_for('sa_metrics', db=component, eid=eid)}"}

            else:
                response = {
                    "Result": "PASS",
                    "Details": f"Component: {component} \n Branch: {git_branch} \n Commit message: {commit_msg} \n No. of files failed to compile:  {compilation_error} \n Current build: {component_version.split('-')[0]} (Commit-{commit_id}) - Defects: {defect_count} \n "
                               f"(No previous records for {git_branch} branch) \n "
                               f"Dashboard Link: http://{ip_addr}:5000{url_for('sa_metrics', db=component, eid=eid)}"}
            if webhook:
                t = threading.Thread(target=post_webhook, args=(response, webhook))
                try:
                    t.start()
                except Exception as e:
                    print(traceback.format_exc())
                    return {"Exception": traceback.format_exc()}
            return response

    except Exception as e:
        print(traceback.format_exc())
        return {"Exception": traceback.format_exc()}


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def post_webhook(response, webhook_url):
    """Hangouts Chat incoming webhook quickstart."""
    url = webhook_url
    msg = f'{response["Details"]}\nResult: {response["Result"]}'
    bot_message = {
        'text': msg}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )

    print(response)


def get_webhook(cursor, db):
    sql = "SELECT Project_Webhook FROM pytesthistoric.SA_PROJECT WHERE Project_Name = %s;"
    val = (db,)
    cursor.execute(sql, val)
    webhook_url = cursor.fetchone()[0]
    return webhook_url


@app.route('/build-version', methods=['POST', 'GET'])
def build_version():
    print(request.form)
    print(request.files)
    cursor = mysql.connection.cursor()
    try:
        if request.method == 'POST':
            comp_versions = request.files['comp-version']
            build_version = request.form['build-version']
            comp_versions = json.load(comp_versions)
            print(comp_versions)
            use_db(cursor, "pytesthistoric")
            cursor.execute(
                f"INSERT INTO BUILD_INFO (Build_Version, Execution_Date) VALUES ('{build_version}', NOW());")
            mysql.connection.commit()
            for comp in comp_versions:
                use_db(cursor, "pytesthistoric")
                commit = comp_versions[comp]["commit"]
                cursor.execute(f"UPDATE BUILD_INFO SET {comp}  = '{commit}' WHERE Build_Version = '{build_version}'")
                use_db(cursor, comp)
                cursor.execute(f"SELECT Execution_Id from SA_EXECUTION WHERE Git_Commit='{commit}' order by Execution_Id desc LIMIT 1;")
                eid = cursor.fetchone()
                if eid:
                    eid = eid[0]
                    cmd = f"UPDATE SA_EXECUTION SET Build_Version = '{build_version}' WHERE Execution_Id = {eid};"
                    print(f"Component {comp} - {cmd}")
                    cursor.execute(cmd)
                else:
                    print(f"Commit {commit} not found for {comp} component")
            mysql.connection.commit()
            return {"Dummy": "Dummy"}
        elif request.method == 'GET':
            use_db(cursor, "pytesthistoric")
            cursor.execute("SELECT * FROM BUILD_INFO;")
            data = cursor.fetchall()
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = N'BUILD_INFO'")
            comps = cursor.fetchall()
            print(f'comps: {comps}')
            master_data = list()
            for commit in data:
                defect_counts = list()
                defect_counts.extend(commit[:3])
                for i in range(3, len(commit)):
                    try:
                        print(f"comp: {comps[i][0]}")
                        use_db(cursor, comps[i][0])
                        cursor.execute(
                            f"SELECT Execution_Id, (Priority_High + Priority_Medium + Priority_Low) as Total_Defects, Component_Version from SA_EXECUTION WHERE Git_Commit='{commit[i]}' order by Execution_Id desc LIMIT 1;")
                        eid = cursor.fetchone()
                        if eid:
                            comp_string = f"{eid[1]} ({eid[2]})"
                            print(f"Append {comp_string}")
                            defect_counts.append(comp_string)

                        else:
                            print(f"Append NA")
                            defect_counts.append("NA")
                    except:
                        print(traceback.print_exc())
                        defect_counts.append("DB NA")
                master_data.append(defect_counts)
            return render_template('build-info.html', data=master_data)
    except Exception as e:
        print(traceback.format_exc())
        return {"Exception": traceback.format_exc()}


def use_db(cursor, db_name):
    cursor.execute("USE %s;" % db_name)


def sort_tests(data_list):
    out = {}
    for elem in data_list:
        try:
            out[elem[1]].extend(elem[2:])
        except KeyError:
            out[elem[1]] = list(elem)
    return [tuple(values) for values in out.values()]


def main():
    args = parse_options()

    app.config['MYSQL_HOST'] = args.sqlhost
    app.config['MYSQL_USER'] = args.username
    app.config['MYSQL_PASSWORD'] = args.password
    app.config['auth_plugin'] = 'mysql_native_password'

    app.run(host=args.apphost)
