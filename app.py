import streamlit as st
import pandas as pd
import os
import hashlib
import platform
import zipfile
import tempfile
import shutil
from datetime import datetime, timedelta

# Tkinter is only available locally on Windows - never on Streamlit Cloud (Linux)
if platform.system() == "Windows":
    import tkinter as tk
    from tkinter import filedialog


# ====================================================
# PAGE CONFIG
# ====================================================

st.set_page_config(
    page_title="Digital Clutter Analyzer",
    page_icon="🗂️",
    layout="wide",
)

st.title("🗂️ Digital Clutter Analyzer")
st.caption("Understand what's taking up space in your folders — no files are ever deleted automatically.")


# ====================================================
# SESSION STATE
# ====================================================

for key, default in {
    "folder_path": "",
    "selected_folder": "",
    "temp_dirs": [],
    "results": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def reset_app():
    for d in st.session_state.temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    st.session_state.folder_path = ""
    st.session_state.selected_folder = ""
    st.session_state.temp_dirs = []
    st.session_state.results = None


# ====================================================
# FOLDER SELECTION
# ====================================================

with st.container(border=True):
    st.subheader("1. Choose a folder")

    if platform.system() == "Windows":
        display_folder = st.session_state.selected_folder or st.session_state.folder_path

        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.text_input("Selected folder", value=display_folder, disabled=True, label_visibility="collapsed", placeholder="No folder selected yet")
        with col_b:
            if st.button("📁 Browse", use_container_width=True):
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                selected_folder = filedialog.askdirectory()
                root.destroy()
                if selected_folder:
                    st.session_state.selected_folder = selected_folder
                    st.session_state.folder_path = selected_folder
                    st.rerun()

    else:
        st.caption("Zip your folder, then upload it below. Max upload size: 1024 MB.")
        uploaded_zip = st.file_uploader("Upload folder as ZIP", type=["zip"], label_visibility="collapsed")

        if uploaded_zip:
            try:
                temp_directory = tempfile.mkdtemp()
                st.session_state.temp_dirs.append(temp_directory)

                zip_path = os.path.join(temp_directory, uploaded_zip.name)
                with open(zip_path, "wb") as f:
                    f.write(uploaded_zip.getbuffer())

                extract_path = os.path.join(temp_directory, "extracted_folder")
                os.makedirs(extract_path, exist_ok=True)

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)

                st.session_state.folder_path = extract_path
                st.success("✅ ZIP uploaded and extracted successfully.")

            except zipfile.BadZipFile:
                st.error("❌ That file isn't a valid ZIP archive. Please re-zip your folder and try again.")
                st.stop()
            except Exception as e:
                st.error(f"❌ Something went wrong while unpacking the ZIP: {e}")
                st.stop()

    folder_path = st.session_state.selected_folder or st.session_state.folder_path

    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        analyze_clicked = st.button("🔍 Analyze Folder", type="primary", disabled=not folder_path, use_container_width=True)
    with btn_col2:
        st.button("🔄 Restart", on_click=reset_app, use_container_width=True)


# ====================================================
# ANALYSIS
# ====================================================

def analyze_folder(folder_path):
    files = []
    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    if not files:
        return None

    # File type breakdown
    file_types, file_type_sizes = {}, {}
    for file in files:
        ext = os.path.splitext(file)[1].lower() or "No Extension"
        try:
            size = os.path.getsize(file)
        except Exception:
            size = 0
        file_types[ext] = file_types.get(ext, 0) + 1
        file_type_sizes[ext] = file_type_sizes.get(ext, 0) + size

    # Large files
    large_files = []
    for file in files:
        try:
            size_mb = os.path.getsize(file) / (1024 * 1024)
            if size_mb > 100:
                large_files.append((file, size_mb))
        except Exception:
            pass

    # Top 5 largest
    all_sizes = []
    for file in files:
        try:
            all_sizes.append((file, os.path.getsize(file) / (1024 * 1024)))
        except Exception:
            pass
    top_5 = sorted(all_sizes, key=lambda x: x[1], reverse=True)[:5]

    # Old files
    cutoff = datetime.now() - timedelta(days=180)
    old_files = []
    for file in files:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file))
            if mtime < cutoff:
                old_files.append((file, mtime))
        except Exception:
            pass

    # Duplicates
    hashes = {}
    for file in files:
        try:
            hasher = hashlib.md5()
            with open(file, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            hashes.setdefault(hasher.hexdigest(), []).append(file)
        except Exception:
            pass

    duplicate_groups = [g for g in hashes.values() if len(g) > 1]
    duplicate_count = sum(len(g) - 1 for g in duplicate_groups)
    duplicate_space = sum(
        os.path.getsize(f) for g in duplicate_groups for f in g[1:] if os.path.exists(f)
    )

    total_size = sum(s for s in file_type_sizes.values())

    # Clutter score
    old_score = min(len(old_files) * 2, 30)
    large_score = min(len(large_files) * 5, 30)
    dup_score = min(duplicate_count * 5, 30)
    count_score = 10 if len(files) > 100 else (5 if len(files) > 50 else 0)
    clutter_score = min(old_score + large_score + dup_score + count_score, 100)

    return {
        "files": files,
        "file_types": file_types,
        "file_type_sizes": file_type_sizes,
        "large_files": large_files,
        "top_5": top_5,
        "old_files": old_files,
        "duplicate_groups": duplicate_groups,
        "duplicate_count": duplicate_count,
        "duplicate_space": duplicate_space,
        "total_size": total_size,
        "clutter_score": clutter_score,
        "score_breakdown": {
            "Old Files": old_score,
            "Large Files": large_score,
            "Duplicates": dup_score,
            "File Count": count_score,
        },
        "analyzed_at": datetime.now(),
    }


if analyze_clicked:
    if not os.path.exists(folder_path):
        st.error("❌ The selected folder does not exist.")
        st.stop()

    with st.spinner("Scanning files..."):
        results = analyze_folder(folder_path)

    if results is None:
        st.warning("📂 This folder does not contain any files.")
        st.stop()

    st.session_state.results = results


# ====================================================
# HELPERS FOR DISPLAY
# ====================================================

def to_display_df(file_size_pairs, base_path, size_label="Size (MB)"):
    rows = []
    for file, size_mb in file_size_pairs:
        rows.append({
            "File": os.path.basename(file),
            "Folder": os.path.dirname(os.path.relpath(file, base_path)) or ".",
            size_label: round(size_mb, 2),
        })
    return pd.DataFrame(rows)


def score_color(score):
    if score <= 20:
        return "🟢", "Low clutter — your folder is relatively organized."
    elif score <= 50:
        return "🟡", "Moderate clutter — some cleanup may be useful."
    elif score <= 75:
        return "🟠", "High clutter — consider reviewing old, large, and duplicate files."
    else:
        return "🔴", "Very high clutter — this folder may need significant cleanup."


# ====================================================
# RESULTS
# ====================================================

results = st.session_state.results

if results:
    st.divider()

    # ---- Top-level metrics ----
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Files", len(results["files"]))
    m2.metric("Total Storage", f"{results['total_size'] / (1024*1024):.1f} MB")
    m3.metric("Duplicates", results["duplicate_count"])
    m4.metric("Reclaimable Space", f"{results['duplicate_space'] / (1024*1024):.1f} MB")

    emoji, message = score_color(results["clutter_score"])
    with st.container(border=True):
        st.markdown(f"### {emoji} Clutter Score: {results['clutter_score']}/100")
        st.progress(results["clutter_score"] / 100)
        st.caption(message)

    st.divider()

    tab_overview, tab_types, tab_large, tab_old, tab_dupes, tab_tips = st.tabs(
        ["📊 Overview", "📁 File Types", "🔴 Large Files", "🕒 Old Files", "♻️ Duplicates", "🧠 Suggestions"]
    )

    # ---- Overview tab ----
    with tab_overview:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Score breakdown**")
            breakdown_df = pd.DataFrame(
                list(results["score_breakdown"].items()), columns=["Category", "Points"]
            )
            st.bar_chart(breakdown_df.set_index("Category"))

        with col2:
            st.markdown("**Cleanup summary**")
            cleanup_df = pd.DataFrame({
                "Category": ["Old Files", "Large Files", "Duplicates"],
                "Count": [len(results["old_files"]), len(results["large_files"]), results["duplicate_count"]],
            })
            st.bar_chart(cleanup_df.set_index("Category"))

        st.markdown("**Top 5 largest files**")
        st.dataframe(
            to_display_df(results["top_5"], folder_path),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("**File categories**")
        categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx", ".xls", ".xlsx"],
            "Audio": [".mp3", ".wav", ".aac", ".flac"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        }
        cat_cols = st.columns(len(categories))
        for col, (cat, exts) in zip(cat_cols, categories.items()):
            count = sum(results["file_types"].get(e, 0) for e in exts)
            col.metric(cat, count)

        st.caption(f"Analysis completed on {results['analyzed_at'].strftime('%d-%m-%Y %I:%M %p')}")

    # ---- File types tab ----
    with tab_types:
        type_df = pd.DataFrame([
            {"Extension": ext, "Files": count, "Size (MB)": round(results["file_type_sizes"][ext] / (1024*1024), 2)}
            for ext, count in results["file_types"].items()
        ]).sort_values("Size (MB)", ascending=False)

        st.dataframe(type_df, use_container_width=True, hide_index=True)
        st.bar_chart(type_df.set_index("Extension")["Size (MB)"], horizontal=True)

    # ---- Large files tab ----
    with tab_large:
        if results["large_files"]:
            st.warning(f"Found {len(results['large_files'])} file(s) larger than 100 MB.")
            df = to_display_df(sorted(results["large_files"], key=lambda x: x[1], reverse=True), folder_path)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No files larger than 100 MB found.")

    # ---- Old files tab ----
    with tab_old:
        if results["old_files"]:
            st.warning(f"Found {len(results['old_files'])} file(s) older than 180 days.")
            rows = []
            for file, mtime in sorted(results["old_files"], key=lambda x: x[1]):
                rows.append({
                    "File": os.path.basename(file),
                    "Folder": os.path.dirname(os.path.relpath(file, folder_path)) or ".",
                    "Last Modified": mtime.strftime("%d-%m-%Y"),
                    "Days Old": (datetime.now() - mtime).days,
                })
            old_df = pd.DataFrame(rows)
            st.dataframe(old_df, use_container_width=True, hide_index=True, height=400)
        else:
            st.success("✅ No files older than 180 days found.")

    # ---- Duplicates tab ----
    with tab_dupes:
        if results["duplicate_groups"]:
            st.warning(
                f"Found {results['duplicate_count']} duplicate file(s) across "
                f"{len(results['duplicate_groups'])} group(s) — "
                f"~{results['duplicate_space'] / (1024*1024):.1f} MB reclaimable."
            )
            for i, group in enumerate(results["duplicate_groups"], start=1):
                with st.expander(f"Group {i}: {os.path.basename(group[0])} ({len(group)} copies)"):
                    rows = []
                    for j, file in enumerate(group):
                        try:
                            size_mb = os.path.getsize(file) / (1024 * 1024)
                        except Exception:
                            size_mb = 0
                        rows.append({
                            "File": os.path.basename(file),
                            "Folder": os.path.dirname(os.path.relpath(file, folder_path)) or ".",
                            "Size (MB)": round(size_mb, 2),
                            "Suggested": "Keep" if j == 0 else "Remove",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.success("✅ No duplicate files found.")

    # ---- Suggestions tab ----
    with tab_tips:
        suggestions = []
        if results["duplicate_count"] > 0:
            suggestions.append("♻️ Review duplicate files and keep only the copies you need.")
        if results["large_files"]:
            suggestions.append("🔴 Review large files and consider moving unnecessary ones to external storage.")
        if results["old_files"]:
            suggestions.append("🕒 Review files that haven't been modified in over 180 days.")
        if len(results["files"]) > 100:
            suggestions.append("📂 This folder has many files — consider organizing into subfolders.")
        if not suggestions:
            suggestions.append("✅ Your folder looks relatively clean. No major cleanup actions are suggested.")

        for s in suggestions:
            st.info(s)

        if results["duplicate_count"] > 0:
            priority = "🔴 High priority: review duplicate files first."
        elif results["large_files"]:
            priority = "🟠 Medium priority: review large files."
        elif results["old_files"]:
            priority = "🟡 Low priority: review old files."
        else:
            priority = "🟢 No major cleanup issues detected."

        st.markdown("**Cleanup priority**")
        st.write(priority)

elif not analyze_clicked:
    st.info("Upload a folder above and click **Analyze Folder** to get started.")


# ====================================================
# ABOUT
# ====================================================

st.divider()
with st.expander("ℹ️ About this tool"):
    st.write(
        "Digital Clutter Analyzer helps you understand what's taking up space in your "
        "folders. It detects large files, old files, and duplicates, and offers cleanup "
        "suggestions — it never deletes anything automatically."
    )