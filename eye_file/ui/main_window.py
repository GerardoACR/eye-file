from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QPlainTextEdit,
    QLineEdit,
    QLabel,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt

from pathlib import Path

from eye_file.data.db import (
    get_db_path,
    connect,
    init_db,
    seed_minimal_data,
    get_default_ids,
    insert_note,
    fetch_categories,
    fetch_note_by_id,
    fetch_notes_for_category_subtree,
)


def build_panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    """
    Small helper to create a framed panel with a title and a vertical layout.

    Why this exists:
    - Keeps the code DRY (Don't Repeat Yourself).
    - Makes it easy to keep consistent padding/spacing across panels.
    """
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setStyleSheet("font-size: 12pt; font-weight: 600;")
    layout.addWidget(title_label)

    return frame, layout


class MainWindow(QMainWindow):
    """
    Main application window.

    MVP layout:
    - Left: Library (documents list + quick search)
    - Middle: Categories tree (filters notes by subtree)
    - Right: Note editor (excerpt + markdown note + page_ref + Save)

    Future responsibilities:
    - Connect UI events (signals) to services (DB, import/export, search).
    - Manage "unsaved changes" logic (Save / Discard / Cancel).
    - Coordinate state: selected document, selected category, current note draft.
    """

    def __init__(self) -> None:
        super().__init__()

        # Window metadata
        self.setWindowTitle("EyeFile")
        self.resize(1200, 750)

        # QSplitter lets the user resize the three panels by dragging dividers.
        splitter = QSplitter(Qt.Horizontal)

        # -------------------------
        # LEFT PANEL: LIBRARY
        # -------------------------
        library_panel, library_layout = build_panel("Library")

        # A search box for filtering documents by title/authors (later: connect to DB/search)
        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Search by title / authors...")
        library_layout.addWidget(self.library_search)

        # Documents list (later populated from the database)
        self.library_list = QListWidget()
        self.library_list.addItem("No documents yet — later: Import PDF")
        library_layout.addWidget(self.library_list)

        # Notes list (filtered by selected category; populated from DB)
        self.notes_list = QListWidget()
        self.notes_list.setObjectName("NotesList")  # optional (for QSS styling later)
        library_layout.addWidget(self.notes_list)

        # Buttons row (placeholder for Import/Open actions)
        lib_buttons = QHBoxLayout()
        self.import_pdf_btn = QPushButton("Import PDF")
        self.open_pdf_btn = QPushButton("Open")
        self.open_pdf_btn.setEnabled(False)  # enabled when a document is selected (later)
        lib_buttons.addWidget(self.import_pdf_btn)
        lib_buttons.addWidget(self.open_pdf_btn)
        library_layout.addLayout(lib_buttons)

        # -------------------------
        # MIDDLE PANEL: CATEGORIES
        # -------------------------
        categories_panel, categories_layout = build_panel("Categories")

        # Search/filter categories (later you can implement subtree filtering on the tree itself)
        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText("Filter categories...")
        categories_layout.addWidget(self.category_search)

        # Category tree (later populated from DB)
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        categories_layout.addWidget(self.category_tree)

        # Buttons row (placeholder for CRUD)
        cat_buttons = QHBoxLayout()
        self.add_cat_btn = QPushButton("+ Add")
        self.rename_cat_btn = QPushButton("Rename")
        self.delete_cat_btn = QPushButton("Delete")
        cat_buttons.addWidget(self.add_cat_btn)
        cat_buttons.addWidget(self.rename_cat_btn)
        cat_buttons.addWidget(self.delete_cat_btn)
        categories_layout.addLayout(cat_buttons)

        # -------------------------
        # RIGHT PANEL: NOTE EDITOR
        # -------------------------
        note_panel, note_layout = build_panel("Note")

        # Excerpt field (plain text)
        note_layout.addWidget(QLabel("Excerpt"))
        self.excerpt_edit = QPlainTextEdit()
        self.excerpt_edit.setPlaceholderText("Excerpt (plain text)...")
        note_layout.addWidget(self.excerpt_edit)

        # Markdown note body
        note_layout.addWidget(QLabel("Note (Markdown)"))
        self.note_md_edit = QPlainTextEdit()
        self.note_md_edit.setPlaceholderText("Note (Markdown)...")
        note_layout.addWidget(self.note_md_edit)

        # Bottom row: page reference + explicit Save
        bottom_row = QHBoxLayout()

        self.page_ref_edit = QLineEdit()
        self.page_ref_edit.setPlaceholderText("page_ref (e.g., p. 37)")
        bottom_row.addWidget(self.page_ref_edit)

        self.save_btn = QPushButton("Save")
        # This objectName is used by your QSS selector:
        # QPushButton#PrimaryAction { ... }
        self.save_btn.setObjectName("PrimaryAction")
        bottom_row.addWidget(self.save_btn)

        note_layout.addLayout(bottom_row)

        # -------------------------
        # Assemble splitter
        # -------------------------
        splitter.addWidget(library_panel)
        splitter.addWidget(categories_panel)
        splitter.addWidget(note_panel)

        # Initial widths (user can resize later)
        splitter.setSizes([320, 320, 560])

        # Root container for the main window
        root_widget = QWidget()
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.addWidget(splitter)

        self.setCentralWidget(root_widget)

        # --- Database bootstrap (MVP minimal) ---
        # project_root points to the repository root (the folder that contains app_data/)
        project_root = Path(__file__).resolve().parents[2]
        db_path = get_db_path(project_root)

        # schema.sql lives inside the package folder: ./eye_file/data/schema.sql
        schema_path = project_root / "eye_file" / "data" / "schema.sql"

        self._conn = connect(db_path)
        init_db(self._conn, schema_path)
        seed_minimal_data(self._conn)
        self.load_categories_tree()

        # Keep track of what note is currently loaded in the editor (for future "Update" support)
        self._current_note_id: int | None = None

        # Connect UI events (signals) to handlers (slots)
        self._connect_signals()

        # Populate notes list for the initially selected category
        self.refresh_notes_list_from_current_category()

        # Quick feedback area at the bottom of the window
        self.statusBar().showMessage("Ready")

        # -----------------------------------------
        # Wiring placeholder (signals) — next step
        # -----------------------------------------
        # For now we keep it simple: no DB, no state.
        # Next milestone will connect:
        # - Import PDF -> add to library + persist in SQLite
        # - Selecting a category -> filter notes list (later)
        # - Save -> insert note into DB with selected doc + category
        #
        # Example pattern (we'll implement soon):
        # self.save_btn.clicked.connect(self.on_save_clicked)

    def on_save_clicked(self) -> None:
        """
        Save the current note draft into SQLite.

        MVP behavior:
        - Uses default document/category ids (placeholder).
        - Later we will replace defaults with selected document + selected category.
        """
        excerpt = self.excerpt_edit.toPlainText().strip()
        body_md = self.note_md_edit.toPlainText().strip()
        page_ref = self.page_ref_edit.text().strip() or None

        # Minimal guard: avoid saving completely empty notes.
        if not (excerpt or body_md):
            self.statusBar().showMessage("Nothing to save (excerpt/note are empty).", 4000)
            return

        # --- Use the selected category from the tree (instead of a default) ---
        selected = self.category_tree.currentItem()
        if selected is None:
            self.statusBar().showMessage("Select a category first.", 4000)
            return

        category_id = selected.data(0, Qt.UserRole)
        if category_id is None:
            self.statusBar().showMessage("Selected category has no id.", 4000)
            return

        category_id = int(category_id)

        # Keep the document as placeholder for now
        document_id, _ = get_default_ids(self._conn)


        note_id = insert_note(
            self._conn,
            document_id=document_id,
            category_id=category_id,
            excerpt=excerpt,
            body_md=body_md,
            page_ref=page_ref,
        )

        self.statusBar().showMessage(f"Saved ✓ (note_id={note_id})", 4000)

        # Optional: clear editors after saving
        self.excerpt_edit.clear()
        self.note_md_edit.clear()
        self.page_ref_edit.clear()
    
        # Refresh the notes list so the new note appears immediately
        self.refresh_notes_list_from_current_category()

        # Optional: select the newly saved note in the list
        for i in range(self.notes_list.count()):
            it = self.notes_list.item(i)
            if it.data(Qt.UserRole) == note_id:
                self.notes_list.setCurrentItem(it)
                break

    
    def load_categories_tree(self) -> None:
        """
        Load categories from SQLite and rebuild the QTreeWidget.

        Each tree item stores its category_id in Qt.UserRole so we can retrieve it later.
        """
        # IMPORTANT: change self.category_tree if your widget is named differently
        tree = self.category_tree

        tree.clear()
        tree.setHeaderHidden(True)

        rows = fetch_categories(self._conn)

        # Build lookup maps
        by_id: dict[int, dict] = {}
        children: dict[int | None, list[int]] = {}

        for r in rows:
            cid = int(r["id"])
            pid = r["parent_id"]
            pid = int(pid) if pid is not None else None
            by_id[cid] = {"id": cid, "name": r["name"], "parent_id": pid}
            children.setdefault(pid, []).append(cid)

        def build_subtree(parent_item: QTreeWidgetItem | None, parent_id: int | None) -> None:
            for cid in children.get(parent_id, []):
                data = by_id[cid]
                item = QTreeWidgetItem([data["name"]])
                item.setData(0, Qt.UserRole, data["id"])  # store category_id

                if parent_item is None:
                    tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                build_subtree(item, data["id"])

        build_subtree(None, None)
        tree.expandAll()

        # Select something by default (so Save always has a category)
        first = tree.topLevelItem(0)
        if first is not None:
            tree.setCurrentItem(first)
    
    def _connect_signals(self) -> None:
        """
        Wire Qt signals (events) to Python methods (handlers).
        Keep all signal hookups in one place to avoid duplicates.
        """
        self.save_btn.clicked.connect(self.on_save_clicked)

        # When the selected category changes, refresh the notes list
        self.category_tree.currentItemChanged.connect(self.on_category_changed)

        # When the user clicks a note in the notes list, load it into the editor
        self.notes_list.itemClicked.connect(self.on_note_clicked)

        # (Optional / later)
        # self.category_search.textChanged.connect(self.on_category_filter_changed)
        # self.library_search.textChanged.connect(self.on_library_search_changed)


    def _selected_category_id(self) -> int | None:
        """
        Read the currently selected category_id from the tree.
        The category_id is stored in Qt.UserRole by load_categories_tree().
        """
        selected = self.category_tree.currentItem()
        if selected is None:
            return None
        cid = selected.data(0, Qt.UserRole)
        return int(cid) if cid is not None else None


    def on_category_changed(self, current, previous) -> None:
        """
        Called when the user selects a different category in the tree.
        MVP behavior: refresh notes list using subtree query.
        """
        cid = self._selected_category_id()
        if cid is None:
            self.notes_list.clear()
            self.notes_list.addItem("No category selected.")
            return

        self.refresh_notes_list(cid)


    def refresh_notes_list_from_current_category(self) -> None:
        """
        Convenience method: refresh notes list using whichever category is selected now.
        """
        cid = self._selected_category_id()
        if cid is None:
            return
        self.refresh_notes_list(cid)


    def refresh_notes_list(self, category_id: int) -> None:
        """
        Fetch notes for the selected category subtree and render them into notes_list.
        Each QListWidgetItem stores note_id in Qt.UserRole.
        """
        self.notes_list.clear()

        rows = fetch_notes_for_category_subtree(self._conn, category_id)

        if not rows:
            placeholder = QListWidgetItem("No notes yet in this category.")
            # Make the placeholder non-selectable
            placeholder.setFlags(Qt.NoItemFlags)
            self.notes_list.addItem(placeholder)
            return

        for r in rows:
            # Be defensive about column names (depends on your SQL)
            note_id = r["id"] if "id" in r.keys() else r.get("note_id")
            note_id = int(note_id)

            excerpt = r["excerpt"] if "excerpt" in r.keys() else (r.get("excerpt") or "")
            excerpt = (excerpt or "").strip()

            page_ref = None
            if "page_ref" in r.keys():
                page_ref = r["page_ref"]
            else:
                page_ref = r.get("page_ref")

            # Nice display text
            display = excerpt if excerpt else "(no excerpt)"
            display = display.replace("\n", " ").strip()
            if len(display) > 70:
                display = display[:67] + "..."

            if page_ref:
                display = f"{display}   [{page_ref}]"

            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, note_id)
            self.notes_list.addItem(item)


    def on_note_clicked(self, item: QListWidgetItem) -> None:
        """
        Load the clicked note into the editor fields.
        """
        note_id = item.data(Qt.UserRole)
        if note_id is None:
            return

        note_id = int(note_id)
        row = fetch_note_by_id(self._conn, note_id)

        if row is None:
            self.statusBar().showMessage(f"Note {note_id} not found.", 4000)
            return

        excerpt = (row["excerpt"] or "") if "excerpt" in row.keys() else (row.get("excerpt") or "")
        body_md = (row["body_md"] or "") if "body_md" in row.keys() else (row.get("body_md") or "")
        page_ref = row["page_ref"] if "page_ref" in row.keys() else row.get("page_ref")

        self.excerpt_edit.setPlainText(excerpt)
        self.note_md_edit.setPlainText(body_md)
        self.page_ref_edit.setText(page_ref or "")

        self._current_note_id = note_id
        self.statusBar().showMessage(f"Loaded note_id={note_id}", 2500)


