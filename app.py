from flask import Flask, render_template, url_for, request, redirect

from flask import session
from flask_mysqldb import MySQL

app = Flask(__name__)

app.secret_key = "DBMS"

# Configure Database
app.config['MYSQL_HOST'] = "127.0.0.1"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "jobportal"


mysql = MySQL(app)

@app.route('/', methods = ['GET', 'POST'])
def login():
    find = 0
    if request.method == 'POST':
        # retrieving the entries made in the login form
        loginDetails = request.form
        email = loginDetails['email']
        password = loginDetails['password']
        cur = mysql.connection.cursor()
        # selecting email and password attributes from jobseeker entity to check if the email and its password exists in the entity
        find = cur.execute("SELECT * FROM jobseeker WHERE (email, password) = (%s, %s) ", (email, password))
        details = cur.fetchall()
        cur.close()
    # login to home page if we find such an entry in the table or redirect to the same page
    if find != 0:
        user = details[0][0]
        session["user"] = user
        print(user)
        return redirect('/home')
    else: 
        if "user" in session:
            return redirect(url_for("home"))
        return render_template('login.html', find = find)

@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # retrieving the entries made in the signup form
        userDetails = request.form
        fname = userDetails['fname']
        lname = userDetails['lname']
        phone_num = userDetails['phone_num']
        address = userDetails['address']
        email = userDetails['email']
        password = userDetails['password']
        cpassword = userDetails['cpassword']
        # checking if the password entered in both the fields are same
        if password == cpassword:
            cur = mysql.connection.cursor()
            # creating a record by inserting the jobseeker details in jobseeker entity
            cur.execute("INSERT INTO jobseeker(first_name, last_name, phone_number, address, email, password) VALUES (%s, %s, %s, %s, %s, %s)",
            (fname, lname, phone_num, address, email, password))
            mysql.connection.commit()
            cur.close()
            # go to login page on submit
            return redirect('/')
        else:
            return redirect('signup')
    return render_template('signup.html')

@app.route('/home', methods = ['GET', 'POST'])
def home():
    if "user" in session:
        user = session["user"]
        cur = mysql.connection.cursor()
        # selecting jobseeker details to display the name of the jobseeker on the home page who is currently logged in
        cur.execute("SELECT * FROM jobseeker WHERE jobseeker_id = {}".format(user))
        userdet = cur.fetchall()
        name = userdet[0][1]
        return render_template('home.html', name = name)
    else:
        return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if "user" in session:
        user = session['user']
        cur = mysql.connection.cursor()

        # Fetch applied jobs
        cur.execute("""
            SELECT job.job_title, job.job_type, company.name, company.location, job.job_salary
            FROM job
            INNER JOIN company ON job.company_id = company.company_id
            WHERE job.job_id IN (SELECT job_id FROM apply WHERE jobseeker_id = %s)
        """, (user,))
        applied_jobs = cur.fetchall()

        # Fetch profile details
        cur.execute("SELECT * FROM profile WHERE jobseeker_id = %s", (user,))
        profile_details = cur.fetchall()
        if profile_details:
            profile_details = profile_details[-1]

        # Fetch resume details
        cur.execute("SELECT * FROM resume WHERE jobseeker_id = %s", (user,))
        resume_details = cur.fetchall()
        if resume_details:
            resume_details = resume_details[-1]  # Get the latest resume entry
        else:
            resume_details = None  # No resume uploaded

        cur.close()

        # Debugging output
        print("Resume Details:", resume_details)

        return render_template('profile.html', applied_jobs=applied_jobs, profile_details=profile_details, resume_details=resume_details)
    else:
        return redirect(url_for('login'))






@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if "user" in session:
        cur = mysql.connection.cursor()  
        if request.method == 'POST':
            searchjob = request.form
            keyword = searchjob['keyword']
            location = searchjob['location']

            # Initialize query variables
            query = """
            SELECT job.job_title, job.job_type, company.name, company.location, 
                   job.job_salary, job.job_description, job.job_id 
            FROM job 
            INNER JOIN company ON job.company_id = company.company_id
            """
            filters = []

            if keyword and not location:
                query += " WHERE (job.job_title LIKE %s) OR (job.job_type LIKE %s) OR (job.job_description LIKE %s)"
                filters.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

            elif location and not keyword:
                query += " WHERE (company.location LIKE %s)"
                filters.append(f"%{location}%")

            elif location and keyword:
                query += """ WHERE ((job.job_title LIKE %s) OR (job.job_type LIKE %s) 
                            OR (job.job_description LIKE %s)) 
                            AND (company.location LIKE %s)"""
                filters.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{location}%"])

            if filters:
                count_search = cur.execute(query, tuple(filters))
                jobsearch = cur.fetchall()
                return render_template('jobsearch.html', jobsearch=jobsearch)

            # If no filters applied, still return with 0 results
            return render_template('jobsearch.html', jobsearch=[])

        # GET method - Display all jobs
        count_jobs = cur.execute("""
        SELECT job.job_title, job.job_type, company.name, company.location, 
               job.job_salary, job.job_description, job.job_id 
        FROM job 
        INNER JOIN company ON job.company_id = company.company_id
        """)

        if count_jobs > 0:
            alljobs = cur.fetchall()
            return render_template('jobs.html', alljobs=alljobs)
        else:
            return render_template('jobs.html', alljobs=[])

    else:
        return redirect(url_for('login'))

@app.route('/manageprofile', methods=['GET', 'POST'])
def manageprofile():
    if "user" in session:
        user = session['user']

        cur = mysql.connection.cursor()
        # Select profile details for the logged-in user
        exist = cur.execute("SELECT * FROM profile WHERE jobseeker_id = %s", (user,))
        profile_data = cur.fetchall()

        if request.method == 'POST':
            profile = request.form
            name= profile['name']
            college = profile['college']
            dept = profile['dept']
            education = profile['education']
            filename = profile['resume']

            # Check if the profile already exists for the user
            if exist > 0:
                # Update existing profile
                cur.execute("UPDATE profile SET name = %s, college = %s, department = %s, education = %s WHERE jobseeker_id = %s", (name, college, dept, education, user))
            else:
                # Insert new profile if it doesn't exist
                cur.execute("INSERT INTO profile (name, college, department, education, jobseeker_id) VALUES (%s, %s, %s, %s, %s)", (name, college, dept, education, user))
            mysql.connection.commit()

            # Resume logic
            cur2 = mysql.connection.cursor()
            res = cur2.execute("SELECT * FROM resume WHERE jobseeker_id = %s", (user,))
            if res > 0:
                # Update existing resume
                cur2.execute("UPDATE resume SET filename = %s WHERE jobseeker_id = %s", (filename, user))
            else:
                # Insert new resume if it doesn't exist
                cur2.execute("INSERT INTO resume (filename, jobseeker_id) VALUES (%s, %s)", (filename, user))
            mysql.connection.commit()
            cur2.close()

            return redirect(url_for('profile'))

        cur.close()

        # Handle empty profile case
        if profile_data:
            return render_template('manageprofile.html', profile_data=profile_data[-1])
        else:
            return render_template('manageprofile.html', profile_data=None)
    else:
        return redirect(url_for('login'))

@app.route('/jobsearch')
def jobsearch():
    if "user" in session:
        return render_template('jobsearch.html')
    else:
        return redirect(url_for('login'))

@app.route('/apply', methods = ['GET', 'POST'])
def apply():
    if "user" in session:
        user = session['user']
        if request.method == 'POST':
            apply = request.form
            jobid = apply['j_id']
            cur = mysql.connection.cursor()
            # select all the jobs the user has applied by using the apply relation table
            applied = cur.execute("SELECT * FROM apply WHERE (jobseeker_id, job_id) = ({}, {})".format(user, jobid))
            if applied == 0:
                # if the user has not applied for that job, then insert a record for the user in the apply table for that job
                cur.execute("INSERT INTO apply VALUES ({}, {})".format(user, jobid))
                mysql.connection.commit()
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))

@app.route('/interviews')
def interviews():
    if "user" in session:
        user = session['user']
        cur = mysql.connection.cursor()

        # Query to check if the user has applied for jobs with scheduled interviews
        check_apply_query = '''
        SELECT * 
        FROM apply 
        INNER JOIN interview 
        ON apply.jobseeker_id = interview.jobseeker_id 
        AND apply.job_id = interview.job_id 
        WHERE interview.jobseeker_id = %s
        '''
        check_apply = cur.execute(check_apply_query, (user,))
        
        if check_apply > 0:
            # Query to fetch interview schedule, job details, and company details for the user
            interview_query = '''
            SELECT interview.jobseeker_id, job.job_title, company.name, interview.date, interview.time 
            FROM job 
            INNER JOIN company ON job.company_id = company.company_id 
            INNER JOIN interview ON interview.job_id = job.job_id 
            WHERE interview.jobseeker_id = %s
            '''
            cur.execute(interview_query, (user,))
            schedule = cur.fetchall()  # Fetch all interview schedules
        else:
            schedule = None

        return render_template('interview.html', schedule=schedule)
    else:
        return redirect(url_for('login'))


@app.route('/results')
def results():
    if "user" in session:
        user = session['user']
        cur = mysql.connection.cursor()
          chk_apply = cur.execute('SELECT * FROM apply INNER JOIN result ON (apply.jobseeker_id, apply.job_id) = (result.jobseeker_id, result.job_id) WHERE result.jobseeker_id = {};'.format(user))
        if chk_apply > 0:
            
            r = cur.execute("SELECT result.jobseeker_id, job.job_title, company.name, company.location, result.status FROM \
            job INNER JOIN company ON job.company_id = company.company_id INNER JOIN result ON result.job_id = job.job_id WHERE result.jobseeker_id = {} AND \
            result.job_id IN (SELECT apply.job_id FROM apply INNER JOIN result ON (apply.jobseeker_id, apply.job_id) = (result.jobseeker_id, result.job_id) WHERE result.jobseeker_id = {});".format(user, user))
            if r > 0:   
                res = cur.fetchall()
            else:
                res = None
        else:
            res = None
        return render_template('results.html', res = res)
    else:
        return redirect(url_for('login'))     

@app.route('/account')
def account():
    if "user" in session:
        user = session["user"]
        cur = mysql.connection.cursor()

        # Fetch personal details
        cur.execute('SELECT * FROM jobseeker WHERE jobseeker.jobseeker_id = {}'.format(user))
        acc = cur.fetchall()

        # Count jobs applied
        cur.execute('SELECT COUNT(*) FROM apply WHERE jobseeker_id = {};'.format(user))
        apply = cur.fetchone()[0]

        # Count interviews scheduled
        cur.execute('SELECT COUNT(*) FROM interview WHERE jobseeker_id = {};'.format(user))
        interview = cur.fetchone()[0]

        # Count all results declared
        cur.execute('SELECT COUNT(*) FROM result WHERE jobseeker_id = {};'.format(user))
        results_declared = cur.fetchone()[0]

        # Count selected results
        cur.execute('SELECT COUNT(*) FROM result WHERE jobseeker_id = {} AND status = "Selected";'.format(user))
        selected_count = cur.fetchone()[0]

        # Count not selected results
        cur.execute('SELECT COUNT(*) FROM result WHERE jobseeker_id = {} AND status != "Selected";'.format(user))
        not_selected_count = cur.fetchone()[0]

        # Render the account template with the calculated counts
        return render_template(
            'account.html',
            acc=acc,
            apply=apply,
            interview=interview,
            results_declared=results_declared,
            selected_count=selected_count,
            not_selected_count=not_selected_count
        )
    else:
        return redirect(url_for("login"))



@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug = True)

