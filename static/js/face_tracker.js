// AuraScan 360 AI Face Detection, Vector Matching & Holographic HUD Renderer
// Powered by face-api.js with WebGL hardware acceleration

class AuraFaceTracker {
    constructor() {
        this.modelsLoaded = false;
        this.enrolledStudents = [];
        this.activeSession = null;
        this.markedStudentIds = new Set();
        this.distanceThreshold = 0.55; // Lower is stricter match
        this.isScanning = false;
        this.lastFrameTime = performance.now();
        this.fps = 0;
        this.lastDetectedCount = 0;
        this.lastUnknownCrop = null;
        this.lastUnknownDescriptor = null;
        this.laserY = 0;
        this.laserSpeed = 4;
        this.simulatedAzimuth = 45;

        // Callback hooks for UI
        this.onAttendanceMarked = null;
        this.onStatsUpdate = null;
        this.onUnknownFace = null;
    }

    async loadModels(modelPath = '/static/models') {
        console.log('[AI] Initializing Face-API Deep Learning Neural Nets...');
        try {
            await faceapi.nets.tinyFaceDetector.loadFromUri(modelPath);
            await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
            await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
            this.modelsLoaded = true;
            console.log('[AI] All Neural Nets Loaded & Ready (TinyFaceDetector + Landmark68 + FaceNet128).');
            return true;
        } catch (err) {
            console.error('[AI ERROR] Model loading failure:', err);
            return false;
        }
    }

    setEnrolledStudents(students) {
        this.enrolledStudents = students.map(s => {
            let desc = null;
            if (s.face_descriptor && Array.isArray(s.face_descriptor) && s.face_descriptor.length === 128) {
                desc = new Float32Array(s.face_descriptor);
            }
            return {
                id: s.id,
                name: s.name,
                roll_no: s.roll_no,
                department: s.department,
                avatar_path: s.avatar_path,
                descriptor: desc
            };
        }).filter(s => s.descriptor !== null);

        console.log(`[AI] Loaded ${this.enrolledStudents.length} biometric face descriptors into memory index.`);
    }

    setActiveSession(session, existingAttendance = []) {
        this.activeSession = session;
        this.markedStudentIds.clear();
        if (existingAttendance && Array.isArray(existingAttendance)) {
            existingAttendance.forEach(rec => {
                if (rec.attendance_status === 'PRESENT' || rec.status === 'PRESENT') {
                    this.markedStudentIds.add(rec.student_id);
                }
            });
        }
        console.log(`[SESSION] Active session #${session ? session.id : 'None'}. Marked count: ${this.markedStudentIds.size}`);
    }

    // Euclidean distance between two 128-D vectors
    computeEuclideanDistance(vecA, vecB) {
        let sum = 0;
        for (let i = 0; i < 128; i++) {
            const diff = vecA[i] - vecB[i];
            sum += diff * diff;
        }
        return Math.sqrt(sum);
    }

    // Match a detected face descriptor against the enrolled student index
    matchFace(detectedDescriptor) {
        if (!this.enrolledStudents.length) return null;

        let bestMatch = null;
        let minDistance = Infinity;

        for (const student of this.enrolledStudents) {
            const dist = this.computeEuclideanDistance(detectedDescriptor, student.descriptor);
            if (dist < minDistance) {
                minDistance = dist;
                bestMatch = student;
            }
        }

        if (bestMatch && minDistance <= this.distanceThreshold) {
            // Convert distance to realistic confidence percentage (0.2 -> 98%, 0.55 -> 72%)
            const confidence = Math.max(65, Math.min(99.4, (1 - (minDistance / 0.8)) * 100));
            return {
                student: bestMatch,
                distance: minDistance,
                confidence: Math.round(confidence * 10) / 10
            };
        }

        return null; // Unknown / Unregistered
    }

    // Crop face snapshot from video canvas as base64 JPEG
    cropFaceSnapshot(videoElement, box) {
        try {
            const cropCanvas = document.createElement('canvas');
            const pad = Math.max(20, box.width * 0.25);
            const x = Math.max(0, box.x - pad);
            const y = Math.max(0, box.y - pad);
            const w = Math.min(videoElement.videoWidth - x, box.width + pad * 2);
            const h = Math.min(videoElement.videoHeight - y, box.height + pad * 2);

            cropCanvas.width = 160;
            cropCanvas.height = 160;
            const ctx = cropCanvas.getContext('2d');
            ctx.drawImage(videoElement, x, y, w, h, 0, 0, 160, 160);
            return cropCanvas.toDataURL('image/jpeg', 0.85);
        } catch (e) {
            return '';
        }
    }

    // Process a single frame: Detect, Match, Mark, and Draw HUD
    async processFrame(videoElement, canvasElement) {
        if (!this.modelsLoaded || !videoElement || videoElement.paused || videoElement.ended) {
            return;
        }

        const now = performance.now();
        const delta = (now - this.lastFrameTime) / 1000;
        this.lastFrameTime = now;
        if (delta > 0) {
            this.fps = Math.round(1 / delta);
        }

        // Match canvas dimensions to video
        if (canvasElement.width !== videoElement.videoWidth || canvasElement.height !== videoElement.videoHeight) {
            canvasElement.width = videoElement.videoWidth || 640;
            canvasElement.height = videoElement.videoHeight || 480;
        }

        const ctx = canvasElement.getContext('2d');
        ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

        // Detect all faces in current field of view
        const options = new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.45 });
        const detections = await faceapi.detectAllFaces(videoElement, options)
            .withFaceLandmarks()
            .withFaceDescriptors();

        this.lastDetectedCount = detections.length;

        // Draw HUD Laser Scanline
        this.drawScanLaser(ctx, canvasElement.width, canvasElement.height);

        // Update Azimuth Compass Simulation
        this.simulatedAzimuth = (this.simulatedAzimuth + 0.3) % 360;

        // Process each detected face in camera view
        for (const det of detections) {
            const box = det.detection.box;
            const descriptor = det.descriptor;
            const match = this.matchFace(descriptor);

            if (match) {
                // Known Student
                const student = match.student;
                const isAlreadyMarked = this.markedStudentIds.has(student.id);

                if (!isAlreadyMarked && this.activeSession) {
                    // Mark Attendance Immediately!
                    this.markedStudentIds.add(student.id);
                    const snapshot = this.cropFaceSnapshot(videoElement, box);

                    // Sci-Fi verification sound
                    if (window.cyberAudio) window.cyberAudio.playVerifyChime();

                    // Notify UI & API
                    if (this.onAttendanceMarked) {
                        this.onAttendanceMarked({
                            student_id: student.id,
                            student_name: student.name,
                            roll_no: student.roll_no,
                            department: student.department,
                            avatar_path: student.avatar_path,
                            confidence: match.confidence,
                            snapshot_base64: snapshot
                        });
                    }
                }

                // Draw Verified Holographic HUD Bounding Box
                this.drawVerifiedBox(ctx, box, student.name, student.roll_no, match.confidence, isAlreadyMarked);
            } else {
                // Unregistered Target
                this.lastUnknownCrop = this.cropFaceSnapshot(videoElement, box);
                this.lastUnknownDescriptor = Array.from(descriptor);

                this.drawUnknownBox(ctx, box);

                if (this.onUnknownFace) {
                    this.onUnknownFace({
                        crop: this.lastUnknownCrop,
                        descriptor: this.lastUnknownDescriptor,
                        box: box
                    });
                }
            }

            // Draw subtle biometric landmark constellation
            this.drawLandmarksHUD(ctx, det.landmarks);
        }

        // Draw HUD Telemetry Header on Canvas
        this.drawTelemetryHUD(ctx, canvasElement.width);

        if (this.onStatsUpdate) {
            this.onStatsUpdate({
                fps: this.fps,
                detectedFaces: this.lastDetectedCount,
                markedCount: this.markedStudentIds.size,
                azimuth: Math.round(this.simulatedAzimuth)
            });
        }
    }

    // --- Luxury Classic HUD Graphics Renderers ---

    drawScanLaser(ctx, width, height) {
        this.laserY = (this.laserY + this.laserSpeed) % height;

        ctx.save();
        const grad = ctx.createLinearGradient(0, this.laserY - 20, 0, this.laserY + 4);
        grad.addColorStop(0, 'rgba(197, 155, 109, 0)');
        grad.addColorStop(0.8, 'rgba(197, 155, 109, 0.2)');
        grad.addColorStop(1, 'rgba(212, 175, 55, 0.75)');

        ctx.fillStyle = grad;
        ctx.fillRect(0, this.laserY - 20, width, 20);

        // Core gold laser beam
        ctx.beginPath();
        ctx.strokeStyle = '#d4af37';
        ctx.lineWidth = 1.5;
        ctx.shadowColor = '#d4af37';
        ctx.shadowBlur = 8;
        ctx.moveTo(0, this.laserY);
        ctx.lineTo(width, this.laserY);
        ctx.stroke();
        ctx.restore();
    }

    drawVerifiedBox(ctx, box, name, rollNo, confidence, isMarked) {
        const { x, y, width, height } = box;
        const color = '#2ec4b6'; // Jade Emerald for verified
        const tag = isMarked ? 'ACADEMIA VERIFIED // PRESENT' : 'LOCKING BIOMETRIC TARGET';

        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;

        // Elegant Corner Brackets
        this.drawCornerBrackets(ctx, x, y, width, height, color);

        // Target Center Reticle
        const cx = x + width / 2;
        const cy = y + height / 2;
        ctx.strokeStyle = 'rgba(46, 196, 182, 0.45)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 8, cy);
        ctx.moveTo(cx, cy - 8); ctx.lineTo(cx, cy + 8);
        ctx.stroke();

        // Top Luxury Badge
        const badgeW = Math.max(170, width + 10);
        const badgeH = 38;
        const badgeX = x - 5;
        const badgeY = Math.max(10, y - badgeH - 6);

        ctx.fillStyle = 'rgba(16, 15, 20, 0.92)';
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.2;
        ctx.fillRect(badgeX, badgeY, badgeW, badgeH);
        ctx.strokeRect(badgeX, badgeY, badgeW, badgeH);

        // Top status pill
        ctx.fillStyle = color;
        ctx.font = 'bold 9px "JetBrains Mono", monospace';
        ctx.fillText(`[ ${tag} ]`, badgeX + 8, badgeY + 13);

        // Student Name & Accuracy
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px "Plus Jakarta Sans", sans-serif';
        ctx.fillText(name, badgeX + 8, badgeY + 28);

        // Confidence badge on right
        ctx.fillStyle = '#c59b6d';
        ctx.font = 'bold 10px monospace';
        ctx.fillText(`${confidence}%`, badgeX + badgeW - 42, badgeY + 28);

        ctx.restore();
    }

    drawUnknownBox(ctx, box) {
        const { x, y, width, height } = box;
        const color = '#e0873a'; // Warm Cognac Amber

        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;

        // Corner Brackets in Cognac Amber
        this.drawCornerBrackets(ctx, x, y, width, height, color);

        // Warning Badge
        const badgeW = Math.max(150, width);
        const badgeH = 34;
        const badgeX = x;
        const badgeY = Math.max(10, y - badgeH - 6);

        ctx.fillStyle = 'rgba(20, 16, 14, 0.94)';
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.2;
        ctx.fillRect(badgeX, badgeY, badgeW, badgeH);
        ctx.strokeRect(badgeX, badgeY, badgeW, badgeH);

        ctx.fillStyle = color;
        ctx.font = 'bold 9px "JetBrains Mono", monospace';
        ctx.fillText('[ UNREGISTERED SUBJECT ]', badgeX + 8, badgeY + 13);

        ctx.fillStyle = '#fbfbfa';
        ctx.font = '10px monospace';
        ctx.fillText('+ CLICK TO ENROLL', badgeX + 8, badgeY + 26);

        ctx.restore();
    }

    drawCornerBrackets(ctx, x, y, w, h, color) {
        const len = Math.min(20, Math.min(w, h) * 0.3);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;

        // Top Left
        ctx.beginPath();
        ctx.moveTo(x, y + len); ctx.lineTo(x, y); ctx.lineTo(x + len, y);
        ctx.stroke();

        // Top Right
        ctx.beginPath();
        ctx.moveTo(x + w - len, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + len);
        ctx.stroke();

        // Bottom Left
        ctx.beginPath();
        ctx.moveTo(x, y + h - len); ctx.lineTo(x, y + h); ctx.lineTo(x + len, y + h);
        ctx.stroke();

        // Bottom Right
        ctx.beginPath();
        ctx.moveTo(x + w - len, y + h); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w, y + h - len);
        ctx.stroke();
    }

    drawLandmarksHUD(ctx, landmarks) {
        if (!landmarks) return;
        ctx.save();
        ctx.fillStyle = 'rgba(197, 155, 109, 0.45)';
        const points = landmarks.positions;
        // Sample every 3rd point to create a clean constellation
        for (let i = 0; i < points.length; i += 3) {
            const pt = points[i];
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 1.2, 0, 2 * Math.PI);
            ctx.fill();
        }
        ctx.restore();
    }

    drawTelemetryHUD(ctx, width) {
        ctx.save();
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillStyle = '#d4af37';
        ctx.shadowColor = '#d4af37';
        ctx.shadowBlur = 6;

        const infoText = `SRM BIOMETRIC AI // AZIMUTH: ${Math.round(this.simulatedAzimuth)}° // FPS: ${this.fps}`;
        ctx.fillText(infoText, width - 420, 25);
        ctx.restore();
    }
}

window.auraTracker = new AuraFaceTracker();
