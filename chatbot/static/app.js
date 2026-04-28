document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Tabs ---
    const navLinks = document.querySelectorAll('.nav-links li');
    const tabContents = document.querySelectorAll('.tab-content');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            // Remove active class from all
            navLinks.forEach(l => l.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked
            link.classList.add('active');
            const targetId = link.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'dashboard') {
                updateDashboardStats();
            }
        });
    });

    // --- Data Fetching & Rendering ---
    let membersData = [];
    let tasksData = [];

    async function fetchMembers() {
        const res = await fetch('/api/members');
        membersData = await res.json();
        renderMembers();
        updateDashboardStats();
    }

    async function fetchTasks() {
        const res = await fetch('/api/tasks');
        tasksData = await res.json();
        renderTasks();
        updateDashboardStats();
    }

    function renderMembers() {
        const list = document.getElementById('members-list');
        list.innerHTML = '';
        membersData.forEach(member => {
            const li = document.createElement('li');
            li.innerHTML = `<span><i class="fa-solid fa-user" style="color:var(--accent-primary); margin-right:8px;"></i> ${member.name}</span>`;
            list.appendChild(li);
        });
    }

    function renderTasks() {
        const list = document.getElementById('tasks-list');
        list.innerHTML = '';
        tasksData.forEach(task => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span>${task.name}</span>
                <span class="priority-badge priority-${task.priority.toLowerCase()}">${task.priority}</span>
            `;
            list.appendChild(li);
        });
    }

    function updateDashboardStats() {
        document.getElementById('stat-total-tasks').textContent = tasksData.length;
        document.getElementById('stat-total-members').textContent = membersData.length;
    }

    // --- Forms ---
    document.getElementById('add-member-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('member-name');
        const name = nameInput.value.trim();
        if (name) {
            await fetch('/api/members', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, availability: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] })
            });
            nameInput.value = '';
            fetchMembers();
        }
    });

    document.getElementById('add-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('task-name');
        const priorityInput = document.getElementById('task-priority');
        const name = nameInput.value.trim();
        const priority = priorityInput.value;
        if (name) {
            await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, priority: priority })
            });
            nameInput.value = '';
            fetchTasks();
        }
    });

    // --- Auto-Schedule ---
    document.getElementById('run-schedule-btn').addEventListener('click', async () => {
        const btn = document.getElementById('run-schedule-btn');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scheduling...';
        
        try {
            const res = await fetch('/api/schedule', { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                renderSchedule(data.tasks, data.distribution);
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error("Scheduling failed:", error);
            alert("Failed to schedule tasks.");
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Auto-Schedule';
        }
    });

    function renderSchedule(scheduledTasks, distribution) {
        const container = document.getElementById('schedule-container');
        container.innerHTML = '';
        
        if (scheduledTasks.length === 0) {
            container.innerHTML = '<p class="empty-state">No tasks to schedule.</p>';
            return;
        }

        // Group tasks by assignee for a cleaner view
        const grouped = {};
        scheduledTasks.forEach(task => {
            if (!grouped[task.assignee]) grouped[task.assignee] = [];
            grouped[task.assignee].push(task);
        });

        for (const [assignee, tasks] of Object.entries(grouped)) {
            const html = `
                <div class="schedule-item">
                    <h4 style="margin-bottom: 0.5rem; color: var(--accent-primary);"><i class="fa-solid fa-user"></i> ${assignee}</h4>
                    <ul style="list-style:none; padding-left:1.5rem; display:flex; flex-direction:column; gap:0.25rem;">
                        ${tasks.map(t => `<li>- ${t.name} <span style="font-size:0.8em; opacity:0.7;">(${t.priority})</span></li>`).join('')}
                    </ul>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', html);
        }
    }

    // --- Chatbot ---
    const chatToggle = document.getElementById('chatbot-toggle');
    const chatWindow = document.getElementById('chatbot-window');
    const chatClose = document.getElementById('chatbot-close');
    const chatRefresh = document.getElementById('chatbot-refresh');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');
    const chatMessages = document.getElementById('chat-messages');

    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('hidden');
    });

    chatClose.addEventListener('click', () => {
        chatWindow.classList.add('hidden');
    });

    chatRefresh.addEventListener('click', () => {
        chatMessages.innerHTML = '<div class="message ai">Hi! I can help you organize chores or give cleaning advice.</div>';
    });

    chatSend.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });

    async function sendChatMessage() {
        const msg = chatInput.value.trim();
        if (!msg) return;

        // Add user message to UI
        addMessage(msg, 'user');
        chatInput.value = '';

        // Show typing indicator
        const typingId = addMessage('...', 'ai');

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            
            // Replace typing indicator with real response
            const typingMsg = document.getElementById(typingId);
            if (typingMsg) {
                // simple formatting for line breaks
                typingMsg.innerHTML = data.reply.replace(/\n/g, '<br>');
            } else {
                addMessage(data.reply, 'ai');
            }
        } catch (error) {
            console.error("Chat error:", error);
            const typingMsg = document.getElementById(typingId);
            if (typingMsg) typingMsg.textContent = "Error connecting to AI.";
        }
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}`;
        div.textContent = text;
        const id = 'msg-' + Date.now();
        div.id = id;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    // Initial fetch
    fetchMembers();
    fetchTasks();
});
