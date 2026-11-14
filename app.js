
const subjects = [
  "Constitution", "Indian Polity", "Governance", "Social Justice",
  "International Relations", "Ancient History", "Medieval History",
  "Modern History", "Art & Culture", "Indian Society",
  "Physical Geography", "Indian Geography", "World Geography",
  "Indian Economy", "Environment & Biodiversity", "Agriculture",
  "Banking", "Space Technology", "Defence", "Internal Security",
  "Disaster Management", "Ethics", "Education", "Health",
  "Government Schemes", "Reports and Indices", "Environment Laws",
  "International Organisations", "Science and Technology",
  "Miscellaneous"
];

const content = document.getElementById("page-content");
const currentAffairs = document.getElementById("current-affairs-content");

let newsItems = [];

function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function getLocalDate(value) {
  if (!value) return null;

  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);

  if (match) {
    return new Date(
      Number(match[1]),
      Number(match[2]) - 1,
      Number(match[3])
    );
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  const date = getLocalDate(value);

  if (!date) return "Date pending";

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric"
  });
}

function showSubjects() {
  content.innerHTML = `
    <h3>UPSC Subject Library</h3>
    <div class="subject-list">
      ${subjects.map((subject, index) => `
        <button class="subject-item" data-subject="${index}">
          ${index + 1}. ${escapeHTML(subject)}
        </button>
      `).join("")}
    </div>
  `;
}

function showSubjectDetail(index) {
  const subject = subjects[index];
  if (!subject) return;

  content.innerHTML = `
    <h3>${escapeHTML(subject)}</h3>
    <p>Study materials and current affairs for this subject will appear here.</p>
    <button id="backToSubjects">Back to Subjects</button>
  `;

  document.getElementById("backToSubjects")
    .addEventListener("click", showSubjects);
}

function showNotes() {
  content.innerHTML = `
    <h3>My Personal Notes</h3>
    <textarea id="notesArea" placeholder="Write your UPSC notes here..."></textarea>
    <button id="saveNotes">Save Notes</button>
    <p id="noteMessage"></p>
  `;

  const notesArea = document.getElementById("notesArea");
  notesArea.value = localStorage.getItem("upscNotes") || "";

  document.getElementById("saveNotes").addEventListener("click", () => {
    localStorage.setItem("upscNotes", notesArea.value);
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
    <div>
      ${bookmarks.length
        ? bookmarks.map(item => `<p>⭐ ${escapeHTML(item)}</p>`).join("")
        : "<p>No bookmarks yet.</p>"}
    </div>
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


function renderArticle(item) {
  const angle = item.upsc_angle || {};

  function renderSection(title, value) {
    if (!value || (Array.isArray(value) && value.length === 0)) {
      return "";
    }

    const content = Array.isArray(value)
      ? `<ul>${value.map(point =>
          `<li>${escapeHTML(point)}</li>`
        ).join("")}</ul>`
      : `<p>${escapeHTML(value)}</p>`;

    return `
      <section class="upsc-note-section">
        <h5>${escapeHTML(title)}</h5>
        ${content}
      </section>
    `;
  }

  const sourceUrl = String(item.source_url || item.id || "");
  const safeUrl = /^https?:\/\//i.test(sourceUrl)
    ? escapeHTML(sourceUrl)
    : "";

  return `
    <article class="news-item">
      <h4>${escapeHTML(item.title)}</h4>

      <p><strong>Date:</strong> ${formatDate(item.date)}</p>
      <p><strong>Source:</strong> ${escapeHTML(item.source || "Unknown")}</p>
      <p><strong>Subject:</strong> ${escapeHTML(item.category || "Miscellaneous")}</p>

      ${renderSection("What happened?", item.summary)}

      <div class="upsc-analysis">
        <h4>UPSC Analysis</h4>

        ${renderSection("1. What is this about?", angle.what_it_is)}

        ${renderSection("2. Why is it important for UPSC?", angle.why_relevant)}

        ${renderSection("3. What does India need?", angle.india_needs)}

        ${renderSection("4. Challenges and concerns", angle.challenges)}

        ${renderSection("5. Way forward", angle.way_forward)}

        ${renderSection("6. Prelims facts", item.prelims_facts)}

        ${renderSection("7. Mains analysis", item.mains_analysis)}

        ${renderSection("8. GS syllabus connection", angle.syllabus)}

        ${!Object.values(angle).some(Boolean) &&
          !item.mains_analysis &&
          !item.prelims_facts?.length
          ? "<p>Detailed UPSC notes are being prepared for this article.</p>"
          : ""}
      </div>

      ${safeUrl ? `
        <p class="pib-source-link">
          <a href="${safeUrl}"
             target="_blank"
             rel="noopener noreferrer"
             style="color:#0866d6;font-weight:700;text-decoration:underline;">
             Read Original PIB Release ↗
          </a>
        </p>
      ` : ""}
    </article>
  `;
}


function renderNews(section = "daily") {
  if (!currentAffairs) return;

  const dated = newsItems.filter(item => getLocalDate(item.date));
  const undated = newsItems.filter(item => !getLocalDate(item.date));

  const now = new Date();
  const today = new Date(
    now.getFullYear(), now.getMonth(), now.getDate()
  );

  let filtered = [...dated];

  if (section === "daily") {
    filtered = dated.filter(item => {
      const date = getLocalDate(item.date);
      return date.toDateString() === today.toDateString();
    });
  } else if (section === "weekly") {
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    filtered = dated.filter(item => {
      const date = getLocalDate(item.date);
      return date >= weekAgo && date <= now;
    });
  } else if (section === "monthly") {
    filtered = dated.filter(item => {
      const date = getLocalDate(item.date);
      return date.getMonth() === now.getMonth() &&
        date.getFullYear() === now.getFullYear();
    });
  }

  const heading =
    section.charAt(0).toUpperCase() + section.slice(1);

  currentAffairs.innerHTML = `
    <h3>${heading} Current Affairs</h3>

    <p>Dated articles: ${filtered.length}</p>

    ${filtered.length
      ? filtered.map(renderArticle).join("")
      : "<p>No dated articles available in this period yet.</p>"
    }

    <hr>

    <h3>Recently Collected — Date Pending</h3>
    <p>These articles have been collected, but their publication dates are not yet available.</p>
    <p>Articles awaiting dates: ${undated.length}</p>

    ${undated.length
      ? undated.map(renderArticle).join("")
      : "<p>No articles are waiting for dates.</p>"
    }
  `;
}

async function loadNews() {
  currentAffairs.innerHTML = "<p>Loading current affairs...</p>";

  try {
    const response = await fetch("data/news.json");

    if (!response.ok) {
      throw new Error("News file could not be loaded.");
    }

    const data = await response.json();
    newsItems = Array.isArray(data) ? data : [];

    renderNews("daily");
  } catch (error) {
    currentAffairs.innerHTML = `
      <h3>Current Affairs</h3>
      <p>Unable to load news right now.</p>
      <p>Please check the news data file and try again.</p>
    `;
    console.error(error);
  }
}

// Main feature buttons
document.querySelectorAll(".feature-card").forEach(button => {
  button.addEventListener("click", () => {
    showFeature(button.dataset.page);
  });
});

// Subject selection
content.addEventListener("click", event => {
  const button = event.target.closest("[data-subject]");
  if (button) {
    showSubjectDetail(Number(button.dataset.subject));
  }
});

// Daily, Weekly and Monthly tabs
document.querySelectorAll(".tab").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(tab => {
      tab.classList.remove("active");
    });

    button.classList.add("active");
    renderNews(button.dataset.section);
  });
});

// Start dashboard
showFeature("subjects");
loadNews();
