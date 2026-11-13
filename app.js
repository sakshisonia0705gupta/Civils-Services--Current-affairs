
const subjects = [
  "Constitution",
  "Indian Polity",
  "Governance",
  "Social Justice",
  "International Relations",
  "Ancient History",
  "Medieval History",
  "Modern History",
  "Art & Culture",
  "Indian Society",
  "Physical Geography",
  "Indian Geography",
  "World Geography",
  "Indian Economy",
  "Environment & Biodiversity",
  "Agriculture",
  "Banking",
  "Space Technology",
  "Defence",
  "Internal Security",
  "Disaster Management",
  "Ethics",
  "Education",
  "Health",
  "Government Schemes",
  "Reports and Indices",
  "Environment Laws",
  "International Organisations",
  "Science and Technology",
  "Miscellaneous"
];

const content = document.getElementById("page-content");
const currentAffairs = document.getElementById("current-affairs-content");

function showSubjects() {
  content.innerHTML = `
    <h3>UPSC Subject Library</h3>
    <div class="subject-list">
      ${subjects.map((subject, index) => `
        <button class="subject-item" data-subject="${index}">
          ${index + 1}. ${subject}
        </button>
      `).join("")}
    </div>
  `;
}

function showNotes() {
  const savedNotes = localStorage.getItem("upscNotes") || "";

  content.innerHTML = `
    <h3>My Personal Notes</h3>
    <textarea id="notesArea"
      placeholder="Write your UPSC notes here...">${savedNotes}</textarea>
    <button id="saveNotes">Save Notes</button>
    <p id="noteMessage"></p>
  `;

  document.getElementById("saveNotes").addEventListener("click", () => {
    const notes = document.getElementById("notesArea").value;
    localStorage.setItem("upscNotes", notes);
    document.getElementById("noteMessage").textContent =
      "Your notes have been saved!";
  });
}

function showBookmarks() {
  const bookmarks = JSON.parse(
    localStorage.getItem("upscBookmarks") || "[]"
  );

  content.innerHTML = `
    <h3>My Bookmarks</h3>
    <p>Saved subjects:</p>
    ${bookmarks.length
      ? bookmarks.map(item => `<p>⭐ ${escapeHTML(item)}</p>`).join("")
      : "<p>No bookmarks yet.</p>"
    }
    <input id="bookmarkInput" placeholder="Enter a topic to bookmark">
    <button id="addBookmark">Add Bookmark</button>
  `;

  document.getElementById("addBookmark").addEventListener("click", () => {
    const input = document.getElementById("bookmarkInput");
    const topic = input.value.trim();

    if (!topic) return;

    bookmarks.push(topic);
    localStorage.setItem("upscBookmarks", JSON.stringify(bookmarks));
    showBookmarks();
  });
}

function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function showFeature(page) {
  if (page === "subjects") {
    showSubjects();
  } else if (page === "notes") {
    showNotes();
  } else if (page === "bookmarks") {
    showBookmarks();
  } else if (page === "tests") {
    content.innerHTML = `
      <h3>Practice Tests</h3>
      <p>Prelims and Mains practice questions will appear here.</p>
    `;
  } else if (page === "revision") {
    content.innerHTML = `
      <h3>Revision Centre</h3>
      <p>Your revision resources will appear here.</p>
    `;
  } else if (page === "pdf") {
    content.innerHTML = `
      <h3>Monthly PDFs</h3>
      <p>Your monthly current affairs PDFs will appear here.</p>
    `;
  }
}

document.querySelectorAll(".feature-card").forEach(button => {
  button.addEventListener("click", () => {
    showFeature(button.dataset.page);
  });
});

document.querySelectorAll(".tab").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(tab =>
      tab.classList.remove("active")
    );

    button.classList.add("active");

    const section = button.dataset.section;

    currentAffairs.innerHTML = `
      <h3>${section.charAt(0).toUpperCase() + section.slice(1)} Current Affairs</h3>
      <p>News and AI-generated UPSC notes will appear here once the news service is connected.</p>
    `;
  });
});

showFeature("subjects");

