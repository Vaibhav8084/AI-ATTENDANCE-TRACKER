import csv
import io
from datetime import datetime
import database

def generate_csv_report(session_id):
    session = database.get_session(session_id)
    if not session:
        return None, "Session not found"

    records = database.get_session_attendance(session_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header Information
    writer.writerow(["=== AURA-SCAN 360 AI CLASSROOM ATTENDANCE REPORT ==="])
    writer.writerow(["Session ID", session["id"]])
    writer.writerow(["Session Name", session["session_name"]])
    writer.writerow(["Course Code", session["course_code"]])
    writer.writerow(["Date & Time", session["date_time"]])
    writer.writerow(["Status", session["status"]])
    writer.writerow(["Total Enrolled", session["total_enrolled"]])
    writer.writerow(["Total Present", session["total_present"]])
    att_rate = round((session["total_present"] / session["total_enrolled"] * 100), 1) if session["total_enrolled"] > 0 else 0
    writer.writerow(["Attendance Rate", f"{att_rate}%"])
    writer.writerow([])
    
    # Table Header
    writer.writerow([
        "Roll No",
        "Student Name",
        "Department",
        "Email",
        "Status",
        "Verified At",
        "Match Confidence (%)"
    ])
    
    for r in records:
        writer.writerow([
            r["roll_no"],
            r["name"],
            r["department"],
            r["email"],
            r["attendance_status"],
            r["timestamp"] if r["timestamp"] else "N/A",
            f"{r['confidence']}%" if r["confidence"] else "N/A"
        ])
        
    return output.getvalue(), None

def generate_html_print_report(session_id):
    session = database.get_session(session_id)
    if not session:
        return None, "Session not found"

    records = database.get_session_attendance(session_id)
    att_rate = round((session["total_present"] / session["total_enrolled"] * 100), 1) if session["total_enrolled"] > 0 else 0
    
    rows_html = ""
    for r in records:
        status_color = "#00ff9d" if r["attendance_status"] == "PRESENT" else "#ff3860"
        rows_html += f"""
        <tr>
            <td style="font-weight:600; font-family: monospace;">{r['roll_no']}</td>
            <td>{r['name']}</td>
            <td>{r['department']}</td>
            <td><span style="color:{status_color}; font-weight:700;">{r['attendance_status']}</span></td>
            <td>{r['timestamp'] if r['timestamp'] else '-'}</td>
            <td>{f"{r['confidence']}%" if r['confidence'] else '-'}</td>
        </tr>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Attendance Report - {session['course_code']} ({session['session_name']})</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1a202c; background: #fff; }}
            .header {{ border-bottom: 3px solid #00f0ff; padding-bottom: 20px; margin-bottom: 25px; }}
            .title {{ font-size: 26px; font-weight: bold; color: #0b1426; text-transform: uppercase; letter-spacing: 1px; }}
            .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; background: #f7fafc; padding: 15px; border-radius: 8px; margin-top: 15px; }}
            .meta-item label {{ font-size: 11px; color: #718096; text-transform: uppercase; font-weight: 700; }}
            .meta-item div {{ font-size: 16px; font-weight: 600; color: #2d3748; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 25px; font-size: 14px; }}
            th {{ background: #0b1426; color: #fff; text-align: left; padding: 12px 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
            td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
            tr:nth-child(even) {{ background: #f8fafc; }}
            .footer {{ margin-top: 40px; text-align: right; font-size: 12px; color: #a0aec0; border-top: 1px solid #edf2f7; padding-top: 10px; }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">AURA-SCAN 360 AI &bull; CLASSROOM ATTENDANCE DOSSIER</div>
            <div style="color: #718096; font-size: 14px; margin-top: 4px;">Automated Deep-Learning Visual Facial Biometrics</div>
            
            <div class="meta">
                <div class="meta-item"><label>Session Name</label><div>{session['session_name']}</div></div>
                <div class="meta-item"><label>Course Code</label><div>{session['course_code']}</div></div>
                <div class="meta-item"><label>Date & Time</label><div>{session['date_time']}</div></div>
                <div class="meta-item"><label>Attendance</label><div>{session['total_present']} / {session['total_enrolled']} ({att_rate}%)</div></div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Roll No</th>
                    <th>Student Name</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Verification Timestamp</th>
                    <th>Match Accuracy</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            Generated by AuraScan 360 AI Attendance Core &bull; Verified Biometric Record
        </div>

        <script>
            window.onload = function() {{ window.print(); }};
        </script>
    </body>
    </html>
    """
    return html, None
