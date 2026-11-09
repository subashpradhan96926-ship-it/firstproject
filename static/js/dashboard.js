// CURRENT DATE
document.getElementById("todayDate").textContent =
    new Date().toDateString();


// DARK MODE
const themeButton = document.getElementById("themeButton");

if (localStorage.getItem("dashboardTheme") === "dark") {
    document.body.classList.add("dark-mode");
    themeButton.textContent = "☀️";
}

themeButton.addEventListener("click", function () {

    document.body.classList.toggle("dark-mode");

    const dark = document.body.classList.contains("dark-mode");

    localStorage.setItem(
        "dashboardTheme",
        dark ? "dark" : "light"
    );

    themeButton.textContent = dark ? "☀️" : "🌙";
});


// TASK ELEMENTS
const taskForm = document.getElementById("taskForm");
const taskInput = document.getElementById("taskInput");
const taskList = document.getElementById("taskList");
const emptyMessage = document.getElementById("emptyMessage");


// LOAD TASKS FROM SQLITE
async function loadTasks() {

    try {

        const response = await fetch("/api/tasks");

        if (!response.ok) {
            throw new Error("Unable to load tasks");
        }

        const tasks = await response.json();

        displayTasks(tasks);

    } catch (error) {
        alert("Could not load tasks. Please refresh the page.");
        console.error(error);
    }
}


// DISPLAY TASKS
function displayTasks(tasks) {

    taskList.innerHTML = "";

    let completed = 0;

    tasks.forEach(function(task) {

        const li = document.createElement("li");

        if (task.completed) {
            li.classList.add("completed");
            completed++;
        }

        // CHECKBOX
        const checkbox = document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.checked = task.completed;

        checkbox.addEventListener("change", async function() {

            const response = await fetch(
                `/api/tasks/${task.id}`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        completed: checkbox.checked
                    })
                }
            );

            if (!response.ok) {
                alert("Could not update task");
                loadTasks();
                return;
            }

            loadTasks();
        });


        // TASK TEXT
        const span = document.createElement("span");

        span.textContent = task.task;


        // DELETE BUTTON
        const deleteButton = document.createElement("button");

        deleteButton.textContent = "×";
        deleteButton.className = "delete-btn";

        deleteButton.addEventListener("click", async function() {

            const response = await fetch(
                `/api/tasks/${task.id}`,
                {
                    method: "DELETE"
                }
            );

            if (!response.ok) {
                alert("Could not delete task");
                return;
            }

            loadTasks();
        });


        li.appendChild(checkbox);
        li.appendChild(span);
        li.appendChild(deleteButton);

        taskList.appendChild(li);

    });


    // EMPTY MESSAGE
    emptyMessage.style.display =
        tasks.length === 0 ? "block" : "none";


    // STATISTICS
    const total = tasks.length;
    const pending = total - completed;

    const percentage = total > 0
        ? Math.round((completed / total) * 100)
        : 0;

    document.getElementById("totalTasks").textContent = total;

    document.getElementById("completedTasks").textContent =
        completed;

    document.getElementById("pendingTasks").textContent =
        pending;

    document.getElementById("completionPercent").textContent =
        percentage + "%";

    document.getElementById("taskProgress").style.width =
        percentage + "%";
}


// ADD TASK
taskForm.addEventListener("submit", async function(event) {

    event.preventDefault();

    const task = taskInput.value.trim();

    if (!task) {
        return;
    }

    try {

        const response = await fetch("/api/tasks", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                task: task
            })

        });

        const result = await response.json();

        if (!response.ok) {
            alert(result.error || "Could not add task");
            return;
        }

        taskInput.value = "";

        loadTasks();

    } catch (error) {
        alert("Server connection failed");
        console.error(error);
    }

});


// CLEAR COMPLETED TASKS
document.getElementById("clearCompleted").addEventListener(
    "click",
    async function() {

        const response = await fetch(
            "/api/tasks/clear-completed",
            {
                method: "DELETE"
            }
        );

        if (!response.ok) {
            alert("Could not clear completed tasks");
            return;
        }

        loadTasks();
    }
);


// SEARCH DASHBOARD
document.getElementById("search").addEventListener(
    "input",
    function() {

        const value = this.value.toLowerCase();

        document.querySelectorAll(".card").forEach(function(card) {

            card.style.display =
                card.innerText.toLowerCase().includes(value)
                ? ""
                : "none";

        });

        document.querySelectorAll("#taskList li").forEach(
            function(item) {

                item.style.display =
                    item.innerText.toLowerCase().includes(value)
                    ? "flex"
                    : "none";

            }
        );
    }
);


// INITIAL LOAD
loadTasks();