import configparser
import json
import logging
import os
import traceback
import uuid
from os import unlink

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
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
                "Create table SA_EXECUTION ( Execution_Id INT NOT NULL auto_increment primary key, Execution_Date DATETIME, Component_Version TEXT, Build_Version TEXT, Pipeline_Link TEXT, Artifact_Link TEXT, Priority_High INT, Priority_Low INT, Priority_Medium INT, Git_Commit TEXT, Git_Url TEXT, Project_Dir TEXT, Commits_After_Tag INT, Git_Branch TEXT);")
            cursor.execute(
                "Create table SA_DEFECT ( Defect_Id INT NOT NULL auto_increment primary key, Execution_Id INT, Defect_Category TEXT, Defect_Check TEXT, Defect_Priority TEXT, Defect_File_Path TEXT, Defect_Function TEXT, Defect_Begin_Line INT, Defect_End_Line INT, Defect_Column INT, Defect_Comment TEXT, Defect_Link TEXT, Defect_Fingerprint TEXT);")
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
            return redirect(url_for('sa-home'))
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
                           graph_data=graph_data)


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
    if request.method == "POST":
        eid_one = request.form['eid_one']
        eid_two = request.form['eid_two']
        cursor = mysql.connection.cursor()
        use_db(cursor, db)
        cursor.execute(f"SELECT * FROM SA_DEFECT WHERE Execution_Id={eid_one} AND Defect_Fingerprint NOT IN "
                       f"(SELECT Defect_Fingerprint FROM  SA_DEFECT WHERE Execution_Id={eid_two});")
        data = cursor.fetchall()
        print(data)
        return render_template('sa-compare.html', data=data, db_name=db)
    else:
        return render_template('sa-compare.html', db_name=db)


@app.route('/<db>/sa-difference', methods=['GET', 'POST'])
def sa_difference(db):
    if request.method == "POST":
        eid_one = request.form['eid_one']
        eid_two = request.form['eid_two']
        cursor = mysql.connection.cursor()
        use_db(cursor, db)
        cursor.execute("SELECT * from SA_DEFECT WHERE Execution_Id=%s;" % eid_one)
        first_data = cursor.fetchall()
        # fetch second eid defect results
        cursor.execute("SELECT * from SA_DEFECT WHERE Execution_Id=%s;" % eid_two)
        second_data = cursor.fetchall()
        # combine both tuples
        data = first_data + second_data
        sorted_data = sort_tests(data)
        return render_template('sa-compare.html', data=sorted_data, db_name=db, fb=eid_one, sb=eid_two)
    else:
        return render_template('sa-compare.html', db_name=db)


def parse_sa_report(csv_file, tool, cursor, eid, commit_url, project_dir, submodule_file, submodule_commits):
    defect_count = 0
    config = configparser.ConfigParser()
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
    # print({section: dict(config[section]) for section in config.sections()})
    if tool == "polyspace":
        # csv_reader = csv.reader(codecs.iterdecode(csv_file, 'utf-8'), delimiter='\t')
        # next(csv_reader) # Skipping header row
        df = pd.read_csv(csv_file, sep='\t', header=[0])
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
    # Update priority counts:
    temp_count = {"high": [],
                  "low": [],
                  "medium": []}
    for priority in temp_count:
        cursor.execute(
            f"SELECT COUNT(Defect_Id) FROM SA_DEFECT WHERE Defect_Priority = '{priority}' AND  Execution_id = {eid};")
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

            if not component_version.isspace() and component_version:
                component_version = f"{component_version}-{git_branch}-{commit_id}" if int(
                    commits_after_tag) > 0 else component_version
            else:
                component_version = "NA"

            tool = request.form['tool']
            cursor = mysql.connection.cursor()
            use_db(cursor, component)
            cmd = f"INSERT INTO SA_EXECUTION (Execution_Date, Component_Version, Pipeline_Link, Artifact_Link, Build_Version, Git_Commit, Git_Url, Project_Dir, Commits_After_Tag, Git_Branch) " \
                  f"VALUES (NOW(), '{component_version}', '{pipeline_link}', '{artifact_link}', '{build_version}', '{commit_id}', '{repo_link}', '{project_dir}', {int(commits_after_tag)}, '{git_branch}');"
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
            if prev_eid:
                prev_eid = prev_eid[0]
                cursor.execute(
                    f"SELECT SUM(Priority_High + Priority_Low + Priority_Medium), Component_Version, Git_Commit FROM SA_EXECUTION WHERE Execution_Id = {prev_eid};")
                temp = cursor.fetchone()
                prev_count = temp[0]
                prev_version = temp[1]
                prev_commit = temp[2]

                if defect_count > prev_count:

                    return {
                        "FAIL": f"Previous build {prev_version.split('-')[0]} (Commit-{prev_commit}) - {prev_count}; "
                                f"Current build {component_version.split('-')[0]} (Commit-{commit_id}) - {defect_count}"}
                else:
                    return {
                        "PASS": f"Previous build {prev_version.split('-')[0]} (Commit-{prev_commit}) - {prev_count}; "
                                f"Current build {component_version.split('-')[0]} (Commit-{commit_id}) - {defect_count}"}
            else:
                return {
                    "PASS": f"Defects added to db - {defect_count} (No previous records for branch - {component_version.split('-')[1]}"}

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
