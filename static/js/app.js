// ==========================================================================
// SRM ACADEMIA & GOOGLE CLASSROOM - MASTER CLIENT PORTAL CONTROLLER
// Executive Classic Luxury Edition (Obsidian, Espresso, Champagne Bronze)
// ==========================================================================

class AcademiaApp {
    constructor() {
        this.currentUser = null;
        this.currentTab = 'classrooms';
        this.classrooms = [];
        this.activeClassroom = null;
        this.activeAttendanceSession = null;
        this.currentStream = null;
        this.selectedCameraId = null;

        this.init();
    }

    async init() {
        console.log('[ACADEMIA] Initializing SRM Academia & Classroom Portal...');
        
        // Check session auth state
        await this.checkAuth();

        // Load AI Deep Learning Models in background
        if (window.auraTracker) {
            window.auraTracker.loadModels('/static/models');
            this.bindAITrackerEvents();
        }

        this.bindEvents();

        // Check SRM live gateway connectivity
        this.checkGatewayStatus();
    }

    // --- Authentication & Session Handling ---

    async checkAuth() {
        try {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.logged_in && data.user) {
                this.currentUser = data.user;
                this.renderPortalForRole();
            } else {
                this.showLoginView();
            }
        } catch (e) {
            this.showLoginView();
        }
    }

    showLoginView() {
        this.currentUser = null;
        document.getElementById('view-login').style.display = 'flex';
        document.getElementById('view-student-portal').style.display = 'none';
        document.getElementById('view-faculty-portal').style.display = 'none';
    }

    renderPortalForRole() {
        document.getElementById('view-login').style.display = 'none';
        
        if (this.currentUser.role === 'teacher') {
            document.getElementById('view-student-portal').style.display = 'none';
            document.getElementById('view-faculty-portal').style.display = 'block';
            this.updateFacultyHeader();
            this.loadFacultyClassrooms();
            this.loadSessions();
        } else {
            document.getElementById('view-faculty-portal').style.display = 'none';
            document.getElementById('view-student-portal').style.display = 'block';
            this.updateStudentHeader();
            this.loadStudentClassrooms();
            this.loadStudentAttendanceMargin();
            this.loadStudentTimetable();
            this.loadStudentMarks();
            this.loadStudentExamSeating();
        }
    }

    updateStudentHeader() {
        const u = this.currentUser;
        document.getElementById('stuHeaderName').innerText = u.name;
        document.getElementById('stuHeaderReg').innerText = u.reg_no || u.net_id;
        document.getElementById('stuHeaderDept').innerText = `${u.department} &bull; ${u.semester}`;
    }

    updateFacultyHeader() {
        const u = this.currentUser;
        document.getElementById('facHeaderName').innerText = u.name;
        document.getElementById('facHeaderDept').innerText = `${u.department} &bull; Faculty`;
    }

    async handleLogin(e, role) {
        e.preventDefault();
        const netIdInput = document.getElementById(role === 'student' ? 'loginNetIdStudent' : 'loginNetIdFaculty');
        const passInput = document.getElementById(role === 'student' ? 'loginPassStudent' : 'loginPassFaculty');

        const netId = netIdInput.value.trim();
        const password = passInput.value.trim();

        const payload = { net_id: netId, password: password, role: role };

        if (role === 'teacher') {
            const sessEl = document.getElementById('loginSessionIdFaculty');
            const captchaEl = document.getElementById('loginCaptchaFaculty');
            if (sessEl && sessEl.value) payload.session_id = sessEl.value;
            if (captchaEl && captchaEl.value) payload.captcha_code = captchaEl.value.trim();
        }

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                this.currentUser = data.user;
                this.showToast(`Authenticated via ${data.gateway || 'SRMIST Gateway'}: Welcome ${data.user.name}`, 'success');
                this.renderPortalForRole();
            } else {
                alert(data.error || 'Login failed');
                if (role === 'teacher') this.refreshEvarsityCaptcha();
            }
        } catch (err) {
            alert('Network error during authentication.');
        }
    }

    async refreshEvarsityCaptcha() {
        const img = document.getElementById('imgEvarsityCaptcha');
        const loading = document.getElementById('captchaLoading');
        const sessInput = document.getElementById('loginSessionIdFaculty');
        const codeInput = document.getElementById('loginCaptchaFaculty');
        if (codeInput) codeInput.value = '';
        if (loading) {
            loading.innerText = 'Fetching...';
            loading.style.display = 'inline';
        }
        if (img) img.style.display = 'none';

        try {
            const res = await fetch('/api/auth/evarsity/captcha');
            const data = await res.json();
            if (data.success && data.captcha_b64) {
                if (img) {
                    img.src = data.captcha_b64;
                    img.style.display = 'block';
                }
                if (loading) loading.style.display = 'none';
                if (sessInput) sessInput.value = data.session_id;
                if (data.demo_code && codeInput) {
                    codeInput.placeholder = data.demo_code;
                }
            }
        } catch (e) {
            if (loading) loading.innerText = 'Offline';
        }
    }

    async checkGatewayStatus() {
        try {
            const res = await fetch('/api/srm/status');
            const data = await res.json();
            const g = data.gateways || {};

            const updatePill = (dotId, textId, info) => {
                const dot = document.getElementById(dotId);
                const text = document.getElementById(textId);
                if (!dot || !text) return;
                if (info && info.online) {
                    dot.className = 'status-dot dot-live';
                    text.innerText = `LIVE (${info.latency_ms}ms)`;
                    text.style.color = 'var(--emerald-safe)';
                } else {
                    dot.className = 'status-dot dot-checking';
                    text.innerText = 'CACHED';
                    text.style.color = 'var(--bronze)';
                }
            };

            updatePill('dotAcademia', 'textAcademia', g.academia);
            updatePill('dotEvarsity', 'textEvarsity', g.evarsity);
            updatePill('dotStaff', 'textStaff', g.staff_finder);
        } catch (e) {
            console.warn('[SRM GATEWAY STATUS] Check error:', e);
        }
    }

    async handleLogout() {
        await fetch('/api/auth/logout', { method: 'POST' });
        this.showToast('Logged out of SRM Academia', 'info');
        this.showLoginView();
    }

    loginAsDemo(role) {
        if (role === 'student') {
            document.getElementById('loginNetIdStudent').value = 'ra2211003010123';
            document.getElementById('loginPassStudent').value = 'password123';
            document.getElementById('formLoginStudent').dispatchEvent(new Event('submit'));
        } else {
            document.getElementById('loginNetIdFaculty').value = 'faculty_srm';
            document.getElementById('loginPassFaculty').value = 'password123';
            document.getElementById('formLoginFaculty').dispatchEvent(new Event('submit'));
        }
    }

    // --- Student Portal Functions ---

    async loadStudentClassrooms() {
        try {
            const res = await fetch(`/api/classrooms?user_id=${this.currentUser.id}&role=student`);
            const data = await res.json();
            this.classrooms = data.classrooms || [];
            this.renderStudentClassroomsGrid();
        } catch (e) {
            console.error(e);
        }
    }

    renderStudentClassroomsGrid() {
        const grid = document.getElementById('studentClassroomsGrid');
        if (!grid) return;
        grid.innerHTML = '';

        if (this.classrooms.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--text-muted);">No classrooms joined yet. Click "+ Join Classroom" using your course code.</div>';
            return;
        }

        this.classrooms.forEach(c => {
            const card = document.createElement('div');
            card.className = 'classroom-card luxury-card';
            card.onclick = () => this.openClassroomStream(c.id);

            card.innerHTML = `
                <div class="classroom-banner">
                    <span class="class-code-tag">${c.code}</span>
                    <div class="class-card-title">${c.name}</div>
                    <div class="class-card-code">${c.course_code} &bull; Sec ${c.section}</div>
                    <div class="class-card-teacher">&#127891; ${c.teacher_name}</div>
                </div>
                <div class="classroom-card-body">
                    <p style="color:var(--text-secondary); font-size:12px;">${c.description || 'Course materials, assignments, and announcements stream.'}</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px;">
                        <span style="font-size:11px; color:var(--bronze); font-family:var(--font-mono);">${c.student_count || 0} Enrolled Students</span>
                        <span style="font-size:12px; color:var(--bronze-light); font-weight:700;">ENTER CLASS &rarr;</span>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    async loadStudentAttendanceMargin() {
        try {
            const res = await fetch(`/api/student/attendance-margin?student_id=${this.currentUser.id}`);
            const data = await res.json();
            
            // Overall hero
            const overall = data.overall;
            const pctEl = document.getElementById('marginHeroPct');
            const statusBadge = document.getElementById('marginHeroBadge');
            const totalHoursEl = document.getElementById('marginTotalHours');
            const attHoursEl = document.getElementById('marginAttHours');
            const marginDial = document.getElementById('marginDialCircle');

            if (pctEl) pctEl.innerText = `${overall.percentage}%`;
            if (totalHoursEl) totalHoursEl.innerText = overall.total_hours;
            if (attHoursEl) attHoursEl.innerText = overall.attended_hours;

            if (statusBadge) {
                statusBadge.className = `margin-hero-badge ${overall.margin_info.status === 'safe' ? 'badge-safe' : 'badge-deficit'}`;
                statusBadge.innerText = overall.margin_info.text.toUpperCase();
            }

            if (marginDial) {
                const offset = 314 - (314 * overall.percentage) / 100;
                marginDial.style.strokeDashoffset = offset;
            }

            // Courses table
            const tbody = document.getElementById('studentCoursesTableBody');
            if (tbody) {
                tbody.innerHTML = '';
                data.courses.forEach(c => {
                    const tr = document.createElement('tr');
                    const badgeClass = c.status === 'safe' ? 'badge-safe' : 'badge-deficit';
                    tr.innerHTML = `
                        <td style="font-family:var(--font-mono); font-weight:700; color:var(--bronze);">${c.course_code}</td>
                        <td style="font-weight:600; color:#fff;">${c.course_name}</td>
                        <td style="color:var(--text-secondary);"><a href="javascript:void(0)" onclick="openStaffFinderModal('${c.faculty_name}')" title="Click to view official SRM faculty profile" style="color:var(--bronze-light); text-decoration:none; border-bottom:1px dashed var(--bronze);">&#128100; ${c.faculty_name}</a></td>
                        <td><strong>${c.attended_hours}</strong> / ${c.total_hours}</td>
                        <td style="font-family:var(--font-mono); font-weight:800; color:${c.percentage >= 75 ? 'var(--emerald-safe)' : 'var(--crimson-alert)'};">${c.percentage}%</td>
                        <td><span class="margin-hero-badge ${badgeClass}" style="padding:4px 10px; font-size:11px;">${c.text}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error('[ATTENDANCE ERROR]', e);
        }
    }

    async loadStudentTimetable() {
        try {
            const res = await fetch(`/api/student/timetable?student_id=${this.currentUser.id}`);
            const data = await res.json();
            const byDay = data.by_day || {};
            const tbody = document.getElementById('studentTimetableBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            for (let day = 1; day <= 5; day++) {
                const periods = byDay[day] || byDay[String(day)] || [];
                const tr = document.createElement('tr');
                let rowHtml = `<td style="font-family:var(--font-heading); font-weight:700; color:var(--bronze); background:rgba(30,27,34,0.5);">DAY ORDER ${day}</td>`;

                for (let hour = 1; hour <= 6; hour++) {
                    const cell = periods.find(p => p.hour === hour);
                    if (cell) {
                        rowHtml += `
                            <td>
                                <div class="timetable-cell-box">
                                    <div class="cell-code">${cell.course_code}</div>
                                    <div class="cell-name">${cell.course_name}</div>
                                    <div class="cell-room">${cell.room_no} &bull; <a href="javascript:void(0)" onclick="openStaffFinderModal('${cell.faculty_name}')" title="Search SRM Staff Directory" style="color:var(--bronze-light); text-decoration:none; border-bottom:1px dashed var(--bronze);">&#128100; ${cell.faculty_name}</a></div>
                                </div>
                            </td>
                        `;
                    } else {
                        rowHtml += `<td><span style="color:var(--text-muted); font-size:11px;">-</span></td>`;
                    }
                }
                tr.innerHTML = rowHtml;
                tbody.appendChild(tr);
            }
        } catch (e) {
            console.error('[TIMETABLE ERROR]', e);
        }
    }

    async loadStudentMarks() {
        try {
            const res = await fetch(`/api/student/marks?student_id=${this.currentUser.id}`);
            const data = await res.json();
            const tbody = document.getElementById('studentMarksBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            data.marks.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-family:var(--font-mono); font-weight:700; color:var(--bronze);">${m.course_code}</td>
                    <td style="font-weight:600; color:#fff;">${m.course_name}</td>
                    <td><strong>${m.cla1}</strong> / 25</td>
                    <td><strong>${m.cla2}</strong> / 25</td>
                    <td><strong>${m.assignment}</strong> / 10</td>
                    <td><strong>${m.model_exam}</strong> / 50</td>
                    <td style="font-family:var(--font-mono); font-weight:800; color:var(--gold);">${m.internal_total} / 60</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('[MARKS ERROR]', e);
        }
    }

    async loadStudentExamSeating() {
        try {
            const res = await fetch(`/api/student/seating?student_id=${this.currentUser.id}`);
            const data = await res.json();
            const grid = document.getElementById('examSeatingGrid');
            if (!grid) return;
            grid.innerHTML = '';

            data.seating_plan.forEach(ex => {
                const card = document.createElement('div');
                card.className = 'luxury-card gold-corner';
                card.style.padding = '20px 24px';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:10px; margin-bottom:14px;">
                        <span style="font-size:11px; color:var(--bronze); font-family:var(--font-mono); font-weight:700;">${ex.course_code}</span>
                        <span class="margin-hero-badge badge-safe" style="font-size:10px;">CONFIRMED HALL TICKET</span>
                    </div>
                    <div style="font-size:16px; font-weight:700; color:#fff;">${ex.course_name}</div>
                    <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">${ex.exam_name}</div>
                    
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; background:rgba(14,13,17,0.6); padding:12px; border-radius:8px;">
                        <div>
                            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">EXAM HALL</div>
                            <div style="font-size:14px; font-weight:700; color:var(--bronze-light); margin-top:2px;">${ex.hall_no}</div>
                        </div>
                        <div>
                            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">SEAT NUMBER</div>
                            <div style="font-size:14px; font-weight:800; font-family:var(--font-mono); color:var(--gold); margin-top:2px;">${ex.seat_no}</div>
                        </div>
                        <div>
                            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">DATE</div>
                            <div style="font-size:12px; color:#fff; margin-top:2px;">${ex.exam_date}</div>
                        </div>
                        <div>
                            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">SESSION & TIME</div>
                            <div style="font-size:12px; color:#fff; margin-top:2px;">${ex.exam_session} &bull; ${ex.exam_time}</div>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        } catch (e) {
            console.error('[SEATING ERROR]', e);
        }
    }

    // --- Google Classroom Stream View (Posts, Photos, Videos) ---

    async openClassroomStream(classId) {
        try {
            const res = await fetch(`/api/classrooms/${classId}`);
            const data = await res.json();
            this.activeClassroom = data.classroom;

            document.getElementById('streamTitle').innerText = data.classroom.name;
            document.getElementById('streamMeta').innerText = `${data.classroom.course_code} &bull; Section ${data.classroom.section} &bull; Class Code: ${data.classroom.code}`;
            document.getElementById('streamCodeDisplay').innerText = data.classroom.code;
            
            this.renderClassroomPosts(data.posts || []);
            this.renderClassroomMembers(data.members || []);

            openModal('modalClassroomStream');
        } catch (e) {
            alert('Failed to load classroom stream.');
        }
    }

    renderClassroomPosts(posts) {
        const list = document.getElementById('classroomPostsList');
        if (!list) return;
        list.innerHTML = '';

        if (posts.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);">No announcements posted yet. Be the first to share something!</div>';
            return;
        }

        posts.forEach(p => {
            const card = document.createElement('div');
            card.className = 'stream-post-card luxury-card';
            let mediaHtml = '';
            if (p.media_url && (p.media_type === 'image' || p.media_url.match(/\.(jpeg|jpg|gif|png|webp)$/i))) {
                mediaHtml = `<div class="post-media-attachment"><img src="${p.media_url}" /></div>`;
            } else if (p.media_url && p.media_type === 'link') {
                mediaHtml = `<div style="margin-top:8px;"><a href="${p.media_url}" target="_blank" style="color:var(--bronze); font-size:12px; text-decoration:underline;">&#128279; ${p.media_url}</a></div>`;
            }

            card.innerHTML = `
                <div class="stream-post-header">
                    <img src="${p.author_avatar || '/static/img/avatar_placeholder.svg'}" class="post-author-avatar" />
                    <div>
                        <div class="post-author-name">${p.author_name} <span style="font-size:11px; color:var(--bronze); font-weight:600;">(${p.author_role})</span></div>
                        <div class="post-timestamp">${p.created_at}</div>
                    </div>
                </div>
                <div class="stream-post-content">${p.content}</div>
                ${mediaHtml}
            `;
            list.appendChild(card);
        });
    }

    renderClassroomMembers(members) {
        const list = document.getElementById('classroomMembersList');
        if (!list) return;
        list.innerHTML = '';

        members.forEach(m => {
            const item = document.createElement('div');
            item.style = 'display:flex; align-items:center; gap:12px; padding:10px; border-bottom:1px solid var(--border-subtle);';
            item.innerHTML = `
                <img src="${m.avatar_path || '/static/img/avatar_placeholder.svg'}" style="width:36px; height:36px; border-radius:50%; border:1px solid var(--bronze);" />
                <div>
                    <div style="font-size:13px; font-weight:700; color:#fff;">${m.name}</div>
                    <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${m.reg_no} &bull; ${m.department}</div>
                </div>
            `;
            list.appendChild(item);
        });
    }

    async submitClassroomPost(e) {
        e.preventDefault();
        if (!this.activeClassroom) return;

        const content = document.getElementById('newPostContent').value.trim();
        const mediaUrl = document.getElementById('newPostMediaUrl').value.trim();
        const mediaType = document.getElementById('newPostMediaType').value;

        if (!content && !mediaUrl) {
            alert('Please enter announcement text or attach a media link.');
            return;
        }

        try {
            const res = await fetch(`/api/classrooms/${this.activeClassroom.id}/posts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: content,
                    author_id: this.currentUser.id,
                    media_url: mediaUrl,
                    media_type: mediaType
                })
            });
            const data = await res.json();
            if (res.ok) {
                this.showToast('Announcement posted to class stream!', 'success');
                document.getElementById('newPostContent').value = '';
                document.getElementById('newPostMediaUrl').value = '';
                this.renderClassroomPosts(data.posts);
            }
        } catch (err) {
            alert('Failed to submit post.');
        }
    }

    async joinClassByCode(e) {
        e.preventDefault();
        const code = document.getElementById('joinClassCodeInput').value.trim();
        if (!code) return;

        try {
            const res = await fetch('/api/classrooms/join', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code, student_id: this.currentUser.id })
            });
            const data = await res.json();
            if (res.ok) {
                this.showToast(data.message, 'success');
                closeModal('modalJoinClass');
                document.getElementById('joinClassCodeInput').value = '';
                await this.loadStudentClassrooms();
            } else {
                alert(data.error || 'Failed to join class.');
            }
        } catch (err) {
            alert('Error joining class.');
        }
    }

    // --- Faculty Portal Functions ---

    async loadFacultyClassrooms() {
        try {
            const res = await fetch(`/api/classrooms?user_id=${this.currentUser.id}&role=teacher`);
            const data = await res.json();
            this.classrooms = data.classrooms || [];
            this.renderFacultyClassroomsGrid();
            this.populateAttendanceClassroomSelector();
        } catch (e) {
            console.error(e);
        }
    }

    renderFacultyClassroomsGrid() {
        const grid = document.getElementById('facultyClassroomsGrid');
        if (!grid) return;
        grid.innerHTML = '';

        this.classrooms.forEach(c => {
            const card = document.createElement('div');
            card.className = 'classroom-card luxury-card';
            card.onclick = () => this.openClassroomStream(c.id);

            card.innerHTML = `
                <div class="classroom-banner">
                    <span class="class-code-tag">${c.code}</span>
                    <div class="class-card-title">${c.name}</div>
                    <div class="class-card-code">${c.course_code} &bull; Sec ${c.section}</div>
                </div>
                <div class="classroom-card-body">
                    <p style="color:var(--text-secondary); font-size:12px;">${c.description || 'Google Classroom Stream active with announcements.'}</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px;">
                        <span style="font-size:11px; color:var(--bronze); font-family:var(--font-mono);">${c.student_count || 0} Students Enrolled</span>
                        <span style="font-size:12px; color:var(--gold); font-weight:700;">MANAGE CLASS &rarr;</span>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    populateAttendanceClassroomSelector() {
        const select = document.getElementById('attendanceClassSelect');
        if (!select) return;
        select.innerHTML = '<option value="">-- Select Class for Attendance Sweep --</option>';
        this.classrooms.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.text = `${c.name} (${c.course_code} - Sec ${c.section})`;
            select.appendChild(opt);
        });
    }

    async handleCreateClassroom(e) {
        e.preventDefault();
        const name = document.getElementById('newClassName').value.trim();
        const code = document.getElementById('newClassCourseCode').value.trim();
        const section = document.getElementById('newClassSection').value.trim();
        const desc = document.getElementById('newClassDesc').value.trim();

        try {
            const res = await fetch('/api/classrooms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    course_code: code,
                    section: section,
                    description: desc,
                    teacher_id: this.currentUser.id
                })
            });
            const data = await res.json();
            if (res.ok) {
                this.showToast(`Classroom created! Code: ${data.class_code}`, 'success');
                closeModal('modalCreateClass');
                document.getElementById('formCreateClass').reset();
                await this.loadFacultyClassrooms();
            } else {
                alert(data.error || 'Failed to create classroom');
            }
        } catch (e) {
            alert('Error creating class.');
        }
    }

    // --- AI Biometric Camera Sweep & Attendance Sync ---

    async startAttendanceSweepForClass() {
        const classId = document.getElementById('attendanceClassSelect').value;
        if (!classId) {
            alert('Please select a classroom from the dropdown first.');
            return;
        }

        const selectedClass = this.classrooms.find(c => c.id == classId);
        if (!selectedClass) return;

        // Fetch enrolled students for this class and load into AI tracker
        const res = await fetch(`/api/students?classroom_id=${classId}`);
        const data = await res.json();
        window.auraTracker.setEnrolledStudents(data.students);

        // Start new session
        const sessRes = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_name: `Live Sweep: ${selectedClass.name}`,
                course_code: selectedClass.course_code,
                classroom_id: selectedClass.id
            })
        });
        const sessData = await sessRes.json();
        this.activeAttendanceSession = sessData.session;
        window.auraTracker.setActiveSession(this.activeAttendanceSession);

        document.getElementById('sweepSessionTitle').innerText = `${selectedClass.name} (${selectedClass.course_code})`;
        this.showToast(`AI Camera Sweep active for ${selectedClass.name}!`, 'success');
        if (window.cyberAudio) window.cyberAudio.playSessionStart();
    }

    bindAITrackerEvents() {
        window.auraTracker.onAttendanceMarked = async (data) => {
            if (!this.activeAttendanceSession) return;
            try {
                const res = await fetch('/api/attendance/mark', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.activeAttendanceSession.id,
                        student_id: data.student_id,
                        confidence: data.confidence,
                        snapshot_base64: data.snapshot_base64
                    })
                });
                const result = await res.json();
                if (result.success && !result.already_marked) {
                    this.addLiveFeedItem(result);
                    this.showToast(`Present: ${result.student_name} (${result.confidence}%)`, 'success');
                }
            } catch (e) {
                console.error(e);
            }
        };

        window.auraTracker.onStatsUpdate = (stats) => {
            const fpsEl = document.getElementById('hudFps');
            const facesEl = document.getElementById('hudFaces');
            const azEl = document.getElementById('hudAzimuth');
            if (fpsEl) fpsEl.innerText = `${stats.fps} FPS`;
            if (facesEl) facesEl.innerText = `${stats.detectedFaces} LOCKED`;
            if (azEl) azEl.innerText = `AZIMUTH: ${stats.azimuth}°`;
        };
    }

    addLiveFeedItem(rec) {
        const feedList = document.getElementById('liveFeedList');
        if (!feedList) return;
        const empty = feedList.querySelector('.feed-empty');
        if (empty) empty.remove();

        const item = document.createElement('div');
        item.style = 'display:flex; align-items:center; gap:12px; background:rgba(26,24,30,0.85); border:1px solid var(--border-gold); padding:8px 12px; border-radius:8px; margin-bottom:8px;';

        item.innerHTML = `
            <img src="${rec.snapshot_path || rec.avatar_path || '/static/img/avatar_placeholder.svg'}" style="width:40px; height:40px; border-radius:6px; object-fit:cover; border:1.5px solid var(--emerald-safe);" />
            <div style="flex:1;">
                <div style="font-size:13px; font-weight:700; color:#fff;">${rec.student_name}</div>
                <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${rec.roll_no} &bull; ${rec.timestamp.split(' ')[1]}</div>
            </div>
            <span class="margin-hero-badge badge-safe" style="font-size:10px;">${rec.confidence}% MATCH</span>
        `;
        feedList.prepend(item);
    }

    async loadSessions() {
        try {
            const res = await fetch('/api/sessions');
            const data = await res.json();
            const tbody = document.getElementById('facultyReportsTableBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            data.sessions.forEach(s => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-family:var(--font-mono); color:var(--bronze); font-weight:700;">#${s.id}</td>
                    <td style="font-weight:600; color:#fff;">${s.session_name}</td>
                    <td style="font-family:var(--font-mono);">${s.course_code}</td>
                    <td style="color:var(--text-muted); font-size:12px;">${s.date_time}</td>
                    <td><strong>${s.total_present}</strong> / ${s.total_enrolled}</td>
                    <td><span class="margin-hero-badge ${s.status === 'ACTIVE' ? 'badge-safe' : ''}">${s.status}</span></td>
                    <td>
                        <a href="/api/export/csv/${s.id}" class="luxury-btn" style="padding:4px 10px; font-size:10px; text-decoration:none;">CSV</a>
                        <a href="/api/export/print/${s.id}" target="_blank" class="luxury-btn btn-gold" style="padding:4px 10px; font-size:10px; text-decoration:none;">DOSSIER</a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {}
    }

    // --- Tab Navigation ---

    switchStudentTab(tabName) {
        document.querySelectorAll('.stu-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.stu-tab-content').forEach(view => {
            view.style.display = view.id === `stu-tab-${tabName}` ? 'block' : 'none';
        });
    }

    switchFacultyTab(tabName) {
        document.querySelectorAll('.fac-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.fac-tab-content').forEach(view => {
            view.style.display = view.id === `fac-tab-${tabName}` ? 'block' : 'none';
        });

        if (tabName === 'camera') {
            this.setupCameraStream();
        }
    }

    async setupCameraStream() {
        const video = document.getElementById('liveVideo');
        const canvas = document.getElementById('videoCanvas');
        if (!video) return;

        try {
            if (!this.currentStream) {
                this.currentStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false
                });
                video.srcObject = this.currentStream;
                await video.play();
            }

            const loop = async () => {
                if (video && !video.paused && !video.ended) {
                    await window.auraTracker.processFrame(video, canvas);
                }
                requestAnimationFrame(loop);
            };
            requestAnimationFrame(loop);
        } catch (err) {
            console.error('Camera access error:', err);
        }
    }

    bindEvents() {
        // Toggle role in login page
        const btnRoleStu = document.getElementById('loginTabStudent');
        const btnRoleFac = document.getElementById('loginTabFaculty');
        const formStu = document.getElementById('formLoginStudent');
        const formFac = document.getElementById('formLoginFaculty');

        if (btnRoleStu && btnRoleFac) {
            btnRoleStu.onclick = () => {
                btnRoleStu.classList.add('active');
                btnRoleFac.classList.remove('active');
                formStu.style.display = 'block';
                formFac.style.display = 'none';
            };
            btnRoleFac.onclick = () => {
                btnRoleFac.classList.add('active');
                btnRoleStu.classList.remove('active');
                formFac.style.display = 'block';
                formStu.style.display = 'none';
                this.refreshEvarsityCaptcha();
            };
        }
    }

    showToast(msg, type = 'info') {
        const toast = document.createElement('div');
        toast.className = 'luxury-card';
        toast.style = 'position:fixed; bottom:24px; right:24px; z-index:99999; padding:12px 20px; font-size:13px; border-color:var(--bronze); box-shadow:0 8px 30px rgba(0,0,0,0.8); background:var(--bg-card);';
        toast.innerHTML = `<span style="color:var(--gold); font-weight:700;">[ACADEMIA]</span> ${msg}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3400);
    }
}

// Global modal helpers
window.openModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('active');
};
window.closeModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
};

document.addEventListener('DOMContentLoaded', () => {
    window.academiaApp = new AcademiaApp();
});
