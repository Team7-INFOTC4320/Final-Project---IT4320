from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

#function interacts with databse
def query_db(query, args=(), one=False):
    conn = sqlite3.connect("reservations.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

#load initial data
@app.route("/init-db")
def init_db():
    with open("schema.sql", "r") as schema_file:
        schema = schema_file.read()
    conn = sqlite3.connect("reservations.db")
    conn.executescript(schema)
    conn.close()
    flash("Database initialized.", "success")
    return redirect(url_for("home"))

#render homepage
@app.route("/")
def home():
    return render_template("index.html")

#admin functions
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # Retrieve admin credentials from the form
        username = request.form['username']
        password = request.form['password']
        
        # Check if the admin exists in the database
        admin = query_db('SELECT * FROM admins WHERE username = ? AND password = ?', [username, password], one=True)
        
        if admin:
            # Fetch the reservations data from the database
            reservations = query_db('SELECT seatRow, seatColumn FROM reservations')

            # Generate the seating chart and calculate total sales
            seating_chart = generate_seating_chart(reservations)
            total_sales = calculate_total_sales()

            # After successful login, render the admin page with the chart and sales info
            return render_template('admin.html', seating_chart=seating_chart, total_sales=total_sales)
        else:
            # If login fails, show an error message
            return render_template('admin.html', error="Invalid username or password")
    
    # Render the login form if no POST request (before login)
    return render_template('admin.html', seating_chart=None, total_sales=None, error=None)

#cost matrix
def get_cost_matrix():
    cost_matrix = [[100, 75, 50, 100] for row in range(12)]
    return cost_matrix

#calculate sales for admin page
def calculate_total_sales():
    cost_matrix = get_cost_matrix()
    total_sales = 0
    
    # Get all reservations from the database
    reservations = query_db('SELECT seatRow, seatColumn FROM reservations')
    
    for reservation in reservations:
        row = reservation['seatRow']
        column = reservation['seatColumn']
        total_sales += cost_matrix[row][column]
    
    return total_sales

#generate ASCII seating chart
def generate_seating_chart(reservations_data):
    # Create an empty 12x4 seating chart
    seating_chart = [['o', 'o', 'o', 'o'] for _ in range(12)]  # 12 rows, 4 columns

    # Iterate over the reservations data and mark reserved seats
    for reservation in reservations_data:
        row = reservation['seatRow']
        column = reservation['seatColumn']
        seating_chart[row][column] = 'x'  # Mark the seat as reserved (x)

    # Convert the seating chart into an ASCII string representation
    chart_str = '\n'.join([' '.join(row) for row in seating_chart])

    return chart_str

@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        seat_row = int(request.form.get("seat_row")) - 1 #counting down choice to prevent index out of range error
        seat_column = int(request.form.get("seat_column")) - 1 #counting down choice to prevent index out of range error
        
        # Check if the seat is already reserved
        reserved_seat = query_db(
            "SELECT * FROM reservations WHERE seatRow = ? AND seatColumn = ?",
            [seat_row, seat_column],
            one=True,
        )
        if reserved_seat:
            flash("This seat is already taken. Please select another.", "error")
            return redirect(url_for("reservations"))
        
        # Generate eTicket and reserve the seat
        eticket = f"{first_name[0]}{last_name[0]}{seat_row}{seat_column}TC4320"
        query_db(
            "INSERT INTO reservations (passengerName, seatRow, seatColumn, eTicketNumber) VALUES (?, ?, ?, ?)",
            [f"{first_name} {last_name}", seat_row, seat_column, eticket],
        )
        flash(f"Reservation confirmed. eTicket: {eticket}", "success")
        return redirect(url_for("reservations"))

    reservations_data = query_db("SELECT * FROM reservations")
    seating_chart = generate_seating_chart(reservations_data)
    return render_template("reservations.html", seating_chart=seating_chart)