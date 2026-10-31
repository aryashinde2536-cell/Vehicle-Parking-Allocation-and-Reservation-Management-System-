
from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
import math
from datetime import datetime

app = Flask(__name__)
DB = "parking.db"
TOTAL_SLOTS = 10
RATE = 20


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def setup():
    con = connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            number TEXT NOT NULL,
            kind TEXT NOT NULL,
            slot INTEGER NOT NULL,
            entry TEXT NOT NULL,
            exit_time TEXT DEFAULT '',
            fee INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Parked'
        )
    """)
    con.commit()
    con.close()


STYLE = """
<style>
body{font-family:Arial;background:#f1f5f9;margin:0;color:#172033}
header{background:#123b65;color:white;padding:18px;text-align:center}
nav{background:#0b2545;padding:12px;text-align:center}
nav a{color:white;text-decoration:none;margin:10px;font-weight:bold}
main{max-width:950px;margin:20px auto;padding:12px}
.box{background:white;padding:18px;margin-bottom:18px;border-radius:10px;
box-shadow:0 2px 8px #ccd2db}
.cards{display:flex;gap:10px;flex-wrap:wrap}
.card{background:#e0f2fe;padding:18px;border-radius:8px;flex:1;min-width:120px}
input,select{width:100%;padding:10px;margin:7px 0 14px;
box-sizing:border-box;border:1px solid #bbb;border-radius:5px}
button,.btn{background:#1769aa;color:white;border:0;padding:10px 14px;
border-radius:5px;text-decoration:none;cursor:pointer;display:inline-block}
.red{background:#c62828}
.green{color:green}.error{color:#c62828}
table{width:100%;border-collapse:collapse;background:white}
th,td{padding:9px;border:1px solid #ddd;text-align:left}
th{background:#123b65;color:white}
.tablewrap{overflow-x:auto}
small{color:#555}
</style>
"""

NAV = """
<header><h1>Vehicle Parking Management</h1>
<p>Parking Allocation and Reservation System</p></header>
<nav>
<a href="/">Dashboard</a>
<a href="/add">Add Vehicle</a>
<a href="/records">Records</a>
</nav>
"""

def page(title, content):
    return render_template_string(
        STYLE + NAV + '<main><h2>' + title + '</h2>' +
        content + '</main>'
    )


@app.route("/")
def home():
    con = connect()
    total = con.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status='Parked'"
    ).fetchone()[0]

    available = TOTAL_SLOTS - total

    rows = con.execute("""
        SELECT * FROM vehicles
        WHERE status='Parked' ORDER BY slot
    """).fetchall()
    con.close()

    slots = ""
    for s in range(1, TOTAL_SLOTS + 1):
        found = any(v["slot"] == s for v in rows)
        color = "#fee2e2" if found else "#dcfce7"
        label = "Occupied" if found else "Available"
        slots += (
            f'<div class="card" style="background:{color}">'
            f'<b>Slot {s}</b><p>{label}</p></div>'
        )

    content = f"""
    <div class="cards">
      <div class="card"><h3>{TOTAL_SLOTS}</h3>Total Slots</div>
      <div class="card"><h3>{total}</h3>Occupied</div>
      <div class="card"><h3>{available}</h3>Available</div>
      <div class="card"><h3>₹{RATE}</h3>Per Hour</div>
    </div>
    <div class="box"><h3>Parking Slots</h3>
    <div class="cards">{slots}</div></div>
    <div class="box">
    <a class="btn" href="/add">+ Add Vehicle</a>
    <a class="btn" href="/records">View Records</a>
    </div>
    """
    return page("Dashboard", content)


@app.route("/add", methods=["GET", "POST"])
def add():
    error = ""

    if request.method == "POST":
        owner = request.form.get("owner", "").strip()
        number = request.form.get("number", "").strip().upper()
        kind = request.form.get("kind", "")
        slot_text = request.form.get("slot", "")

        if not owner or not number or not slot_text:
            error = "Please fill all fields."
        elif kind not in ("Two Wheeler", "Four Wheeler", "Other"):
            error = "Select a valid vehicle type."
        else:
            try:
                slot = int(slot_text)
            except ValueError:
                slot = 0

            if slot < 1 or slot > TOTAL_SLOTS:
                error = "Invalid parking slot."
            else:
                con = connect()

                occupied = con.execute("""
                    SELECT id FROM vehicles
                    WHERE slot=? AND status='Parked'
                """, (slot,)).fetchone()

                duplicate = con.execute("""
                    SELECT id FROM vehicles
                    WHERE UPPER(number)=? AND status='Parked'
                """, (number,)).fetchone()

                if occupied:
                    error = "This slot is already occupied."
                elif duplicate:
                    error = "This vehicle is already parked."
                else:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    con.execute("""
                        INSERT INTO vehicles
                        (owner,number,kind,slot,entry,status)
                        VALUES(?,?,?,?,?,'Parked')
                    """, (owner, number, kind, slot, now))
                    con.commit()
                    con.close()
                    return redirect(url_for("records"))

                con.close()

    content = """
    <div class="box">
    <p class="error">""" + error + """</p>
    <form method="POST">
    <label>Owner Name</label>
    <input name="owner" required>
    <label>Vehicle Number</label>
    <input name="number" placeholder="MH12AB1234" required>
    <label>Vehicle Type</label>
    <select name="kind" required>
      <option value="Two Wheeler">Two Wheeler</option>
      <option value="Four Wheeler">Four Wheeler</option>
      <option value="Other">Other</option>
    </select>
    <label>Parking Slot</label>
    <select name="slot" required>
    """
    con = connect()
    occupied = con.execute("""
        SELECT slot FROM vehicles WHERE status='Parked'
    """).fetchall()
    busy = [v["slot"] for v in occupied]
    con.close()

    for s in range(1, TOTAL_SLOTS + 1):
        if s not in busy:
            content += f'<option value="{s}">Slot {s}</option>'

    content += """
    </select>
    <button type="submit">Park Vehicle</button>
    </form></div>
    """
    return page("Add Vehicle", content)


@app.route("/records")
def records():
    con = connect()
    rows = con.execute(
        "SELECT * FROM vehicles ORDER BY id DESC"
    ).fetchall()
    con.close()

    body = """
    <div class="box"><a class="btn" href="/add">+ Add Vehicle</a>
    <div class="tablewrap"><table>
    <tr><th>ID</th><th>Owner</th><th>Number</th><th>Type</th>
    <th>Slot</th><th>Entry</th><th>Status</th><th>Fee</th><th>Actions</th></tr>
    """

    for v in rows:
        actions = ""
        if v["status"] == "Parked":
            actions = (
                f'<a class="btn" href="/edit/{v["id"]}">Edit</a> '
                f'<form method="POST" action="/exit/{v["id"]}" '
                'style="display:inline">'
                '<button type="submit">Vehicle Exit</button></form>'
            )
        else:
            actions = (
                f'<small>Exit: {v["exit_time"]}</small><br>'
                f'<form method="POST" action="/delete/{v["id"]}" '
                'style="display:inline">'
                '<button class="red" type="submit">Delete</button></form>'
            )

        body += f"""
        <tr>
        <td>{v['id']}</td>
        <td>{v['owner']}</td>
        <td>{v['number']}</td>
        <td>{v['kind']}</td>
        <td>{v['slot']}</td>
        <td>{v['entry']}</td>
        <td>{v['status']}</td>
        <td>₹{v['fee']}</td>
        <td>{actions}</td>
        </tr>
        """

    body += "</table></div></div>"
    return page("Vehicle Records", body)


@app.route("/edit/<int:vid>", methods=["GET", "POST"])
def edit(vid):
    con = connect()
    v = con.execute(
        "SELECT * FROM vehicles WHERE id=?", (vid,)
    ).fetchone()

    if v is None:
        con.close()
        return "Record not found.", 404

    if v["status"] != "Parked":
        con.close()
        return redirect(url_for("records"))

    error = ""

    if request.method == "POST":
        owner = request.form.get("owner", "").strip()
        number = request.form.get("number", "").strip().upper()
        kind = request.form.get("kind", "")

        if not owner or not number:
            error = "Enter owner name and vehicle number."
        elif kind not in ("Two Wheeler", "Four Wheeler", "Other"):
            error = "Select a valid vehicle type."
        else:
            duplicate = con.execute("""
                SELECT id FROM vehicles
                WHERE UPPER(number)=? AND status='Parked' AND id<>?
            """, (number, vid)).fetchone()

            if duplicate:
                error = "This vehicle number is already parked."
            else:
                con.execute("""
                    UPDATE vehicles SET owner=?, number=?, kind=?
                    WHERE id=?
                """, (owner, number, kind, vid))
                con.commit()
                con.close()
                return redirect(url_for("records"))

    con.close()

    content = """
    <div class="box">
    <p class="error">""" + error + """</p>
    <form method="POST">
    <label>Owner Name</label>
    <input name="owner" value=""" + repr(v["owner"]) + """ required>
    <label>Vehicle Number</label>
    <input name="number" value=""" + repr(v["number"]) + """ required>
    <label>Vehicle Type</label>
    <select name="kind">
    """
    for kind in ("Two Wheeler", "Four Wheeler", "Other"):
        selected = "selected" if v["kind"] == kind else ""
        content += f'<option {selected}>{kind}</option>'

    content += """
    </select><button type="submit">Save Changes</button>
    </form></div>
    """
    return page("Edit Vehicle", content)


@app.route("/exit/<int:vid>", methods=["POST"])
def vehicle_exit(vid):
    con = connect()
    v = con.execute(
        "SELECT * FROM vehicles WHERE id=?", (vid,)
    ).fetchone()

    if v and v["status"] == "Parked":
        entry = datetime.strptime(
            v["entry"], "%Y-%m-%d %H:%M:%S"
        )
        now = datetime.now()
        hours = max(1, math.ceil((now - entry).total_seconds() / 3600))
        fee = hours * RATE
        exit_time = now.strftime("%Y-%m-%d %H:%M:%S")

        con.execute("""
            UPDATE vehicles
            SET exit_time=?, fee=?, status='Exited'
            WHERE id=?
        """, (exit_time, fee, vid))
        con.commit()

    con.close()
    return redirect(url_for("records"))


@app.route("/delete/<int:vid>", methods=["POST"])
def delete(vid):
    con = connect()
    con.execute("""
        DELETE FROM vehicles
        WHERE id=? AND status='Exited'
    """, (vid,))
    con.commit()
    con.close()
    return redirect(url_for("records"))


if __name__ == "__main__":
    setup()
    print("Parking Management System is starting...")
    print("Open your browser at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
