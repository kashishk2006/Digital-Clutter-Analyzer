import streamlit as st
import pandas as pd
import os
import hashlib
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta

def select_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory()

    root.destroy()

    return folder

st.title("🗂️ Digital Clutter Analyzer")

st.write(
    "Analyze your folder, identify digital clutter, and discover opportunities to free up storage."
)

st.info(
    "💡 Tip: Select any folder you want to analyze and discover old, large, and duplicate files."
)
if "folder_path" not in st.session_state:
    st.session_state.folder_path = ""


def reset_app():
    st.session_state.folder_path = ""


def browse_folder():
    selected_folder = select_folder()

    if selected_folder:
        st.session_state.folder_path = selected_folder


st.text_input(
    "Selected Folder:",
    key="folder_path"
)

st.button(
    "📁 Browse for Folder",
    on_click=browse_folder
)
st.button(
    "🔄 Restart",
    on_click=reset_app
)


folder_path = st.session_state.folder_path
if folder_path:
    st.success(f"Selected folder: {folder_path}")

if st.button("Analyze Folder"):

    if os.path.exists(folder_path):

        files = []

        for root, folders, filenames in os.walk(folder_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))

        if not files:
            st.warning("⚠️ This folder does not contain any files to analyze.")
            st.stop()

        st.success("Folder analyzed successfully!")
        st.header("📊 Folder Analysis Dashboard")

        # Total Storage
        total_size = 0

        for file in files:
            total_size += os.path.getsize(file)

        total_size_mb = total_size / (1024 * 1024)

        col1, col2 = st.columns(2)

        col1.metric("📁 Total Files", len(files))
        col2.metric("💾 Total Storage", f"{total_size_mb:.2f} MB")
        st.divider()

        # File Type Breakdown
        st.subheader("📂 File Type Breakdown")

        file_types = {}
        file_type_sizes = {}

        for file in files:
            extension = os.path.splitext(file)[1].lower()

            if extension == "":
                extension = "No Extension"

            if extension in file_types:
                file_types[extension] += 1
            else:
                file_types[extension] = 1

            file_size = os.path.getsize(file)

            if extension in file_type_sizes:
                file_type_sizes[extension] += file_size
            else:
                file_type_sizes[extension] = file_size

        for extension, count in file_types.items():
            size_mb = file_type_sizes[extension] / (1024 * 1024)
            st.write(f"{extension}: {count} files — {size_mb:.2f} MB")

        chart_data = pd.DataFrame(
            list(file_type_sizes.items()),
            columns=["File Type", "Storage"]
        )

        chart_data["Storage"] = chart_data["Storage"] / (1024 * 1024)
        st.bar_chart(
            chart_data.set_index("File Type"),
            horizontal=True
        )


        # Large Files
        st.subheader("🔴 Large Files")

        large_files = []

        for file in files:
            size_mb = os.path.getsize(file) / (1024 * 1024)

            if size_mb > 100:
                large_files.append((file, size_mb))

        if large_files:
            for file, size_mb in large_files:
                st.write(
                    f"📄 {os.path.basename(file)} — {size_mb:.2f} MB"
                )
        else:
            st.write("No large files found.")

        # Old Files
        st.subheader("🕒 Old Files")

        old_files = []

        cutoff_date = datetime.now() - timedelta(days=180)

        for file in files:
            modified_time = datetime.fromtimestamp(
                os.path.getmtime(file)
            )

            if modified_time < cutoff_date:
                old_files.append((file, modified_time))

        if old_files:
            for file, modified_time in old_files:
                days_old = (datetime.now() - modified_time).days

                st.write(
                    f"📄 {os.path.basename(file)} — {days_old} days old"
                )
        else:
            st.write("No files older than 180 days found.")

        # Duplicate Files
        st.subheader("♻️ Duplicate Files")

        file_hashes = {}

        for file in files:
            try:
                with open(file, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

                if file_hash in file_hashes:
                    file_hashes[file_hash].append(file)
                else:
                    file_hashes[file_hash] = [file]

            except:
                pass

        duplicates_found = False

        for file_hash, duplicate_files in file_hashes.items():

            if len(duplicate_files) > 1:

                duplicates_found = True

                st.write("🔁 Duplicate group:")

                for file in duplicate_files:
                    st.write(f"📄 {os.path.basename(file)}")

        if not duplicates_found:
            st.write("No duplicate files found.")

        # Clutter Score
        st.subheader("📊 Clutter Score")
        st.caption("A higher score means more digital clutter was detected.")

        score = 0
    
        # Old files
        score += min(len(old_files) * 2, 30)

        # Large files
        score += min(len(large_files) * 5, 30)
         # Top 5 Largest Files
        st.subheader("🏆 Top 5 Largest Files")

        sorted_files = sorted(
            files,
            key=lambda file: os.path.getsize(file),
            reverse=True
        )

        for file in sorted_files[:5]:
            size_mb = os.path.getsize(file) / (1024 * 1024)

            st.write(
                f"📄 {os.path.basename(file)} — {size_mb:.2f} MB"
            )

        # Duplicate files
        duplicate_count = 0

        for file_hash, duplicate_files in file_hashes.items():
            if len(duplicate_files) > 1:
                duplicate_count += len(duplicate_files) - 1

        score += min(duplicate_count * 5, 30)
        old_points = min(len(old_files) * 2, 30)
        large_points = min(len(large_files) * 5, 30)
        duplicate_points = min(duplicate_count * 5, 30)
        # Number of files
        if len(files) > 100:
            file_count_points = 10
        elif len(files) > 50:
            file_count_points = 5
        else:
            file_count_points = 0

        score += file_count_points

        score = min(score, 100)

        st.metric("📊 Clutter Score", f"{score}/100")
        st.progress(score / 100)
        st.caption(
            "Score is based on old files, large files, duplicate files, and overall file count."
        )
        st.write("**Score Breakdown:**")
        st.write(f"🕒 Old Files: +{old_points} points")
        st.write(f"🔴 Large Files: +{large_points} points")
        st.write(f"♻️ Duplicate Files: +{duplicate_points} points")
        st.write(f"📁 File Count: +{file_count_points} points")

        # Explain the score
        if score <= 30:
            st.success("🟢 Low Clutter — Your folder is relatively organized and contains little unnecessary clutter.")

        elif score <= 60:
            st.info("🟡 Moderate Clutter — Your folder contains some old, large, or duplicate files that could be cleaned up.")

        elif score <= 80:
            st.warning("🟠 High Clutter — Your folder contains a significant amount of old, large, or duplicate files.")

        else:
            st.error("🔴 Very High Clutter — Your folder contains a large amount of digital clutter and may need significant cleanup.")
         # Potential Space to Free
        st.subheader("💾 Potential Space to Free")

        duplicate_space = 0

        for file_hash, duplicate_files in file_hashes.items():

            if len(duplicate_files) > 1:

                for file in duplicate_files[1:]:
                    try:
                        duplicate_space += os.path.getsize(file)
                    except:
                        pass

        duplicate_space_mb = duplicate_space / (1024 * 1024)

        st.metric(
            "Potential Space to Free",
            f"{duplicate_space_mb:.2f} MB"
        )
        st.caption(
            "This is the storage that could potentially be recovered by removing duplicate files."
        )
        # Cleanup Summary
        st.subheader("🧹 Cleanup Summary")

        st.write(
            f"Your folder contains {len(files)} files, "
            f"including {len(large_files)} large files, "
            f"{len(old_files)} old files, and "
            f"{duplicate_count} duplicate files."
        )
        st.info(
            f"💾 Potential space to free from duplicates: "
            f"{duplicate_space_mb:.2f} MB"
        )
        cleanup_data = pd.DataFrame(
            {
                "Category": ["Old Files", "Large Files", "Duplicates"],
                "Files": [
                    len(old_files),
                    len(large_files),
                    duplicate_count
                ]
            }
        )

        st.bar_chart(
            cleanup_data.set_index("Category")
        )
         # Cleanup Priority
        st.subheader("🚨 Cleanup Priority")

        if duplicate_count > 0:
            st.error("🔴 High Priority — Review duplicate files first.")

        elif len(large_files) > 0:
            st.warning("🟠 Medium Priority — Review large files to free storage.")

        elif len(old_files) > 0:
            st.info("🟡 Low Priority — Review old files that may no longer be needed.")

        else:
            st.success("🟢 No Immediate Cleanup Needed — Your folder looks organized.")

        # File Categories
        st.subheader("🗃️ File Categories")

        categories = {
            "📄 Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
            "🖼️ Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "📦 Archives": [".zip", ".rar", ".7z"],
            "⚙️ Installers": [".exe", ".msi", ".dmg"],
        }

        category_cols = st.columns(4)

        for i, (category, extensions) in enumerate(categories.items()):

            count = 0

            for extension in extensions:
                count += file_types.get(extension, 0)

            category_cols[i].metric(category, f"{count} files")
        # Smart Cleanup Suggestions
        st.subheader("🧠 Smart Cleanup Suggestions")

        suggestions = []

        if len(old_files) > 0:
            suggestions.append(
                f"🕒 You have {len(old_files)} old files that haven't been modified in over 180 days."
            )

        if len(large_files) > 0:
            suggestions.append(
                f"🔴 You have {len(large_files)} large files taking up significant storage."
            )

        if duplicate_count > 0:
            suggestions.append(
                f"♻️ You have {duplicate_count} duplicate files that could potentially be removed."
            )

        if len(file_types) > 5:
            suggestions.append(
                "📂 Your folder contains many different file types. Consider organizing them into separate folders."
            )

        if not suggestions:
            suggestions.append(
                "🟢 Your folder looks well organized. No major cleanup issues were detected."
            )

        for suggestion in suggestions:
            st.write(suggestion)

        st.caption(
            f"🕒 Analysis completed on {datetime.now().strftime('%d %B %Y, %I:%M %p')}"
        )

        st.divider()
        
        st.subheader("ℹ️ About Digital Clutter Analyzer")
        st.write(
            "Digital Clutter Analyzer helps identify old, large, and duplicate files "
            "so you can understand what is taking up space and decide what to clean up."
        )

    else:
        st.error("Folder not found. Please check the path.")