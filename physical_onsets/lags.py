"""
Calculation and plotting of lags between events onsets and Pulses.

Events onsets refer to the physical onsets of its display and pulses
represent CPU times.

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 19th of March 2026
Last Update: April 2026

Compatibility: Python 3.10.16
"""

import glob
import os

import matplotlib.pyplot as plt
import pandas as pd

# =====================================================================
# Functions
# =====================================================================


def load_tsv_files(input_dir, filename_filter=None):
    """Load and stack all TSV files from the input directory."""
    pattern = os.path.join(input_dir, "*.tsv")
    file_list = sorted(glob.glob(pattern))

    if filename_filter is not None:
        file_list = [
            fpath for fpath in file_list
            if filename_filter(os.path.basename(fpath))
        ]

    if not file_list:
        raise FileNotFoundError(
            f"No TSV files found in input directory:\n{input_dir}"
        )

    dataframes = []

    for fpath in file_list:
        df = pd.read_csv(fpath, sep="\t")
        df["source_file"] = os.path.basename(fpath)
        dataframes.append(df)

    return pd.concat(dataframes, ignore_index=True)


def load_single_tsv(file_path):
    """Load one TSV file."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Input file not found:\n{file_path}")

    return pd.read_csv(file_path, sep="\t")


def extract_task_from_filename(filename):
    """Extract task label from filename."""
    name = filename.lower()

    if "ntfd" in name:
        return "ntfd"

    if "percep" in name or "perception" in name:
        return "percep"

    if "prod" in name or "production" in name:
        return "prod"

    return None


def extract_buffer_from_filename(filename):
    """Extract buffer tag from filename."""
    name = filename.lower()

    for tag in ["buf-01", "buf-05", "buf-08"]:
        if tag in name:
            return tag

    return None


def prepare_lag_data(df):
    """Prepare lag data for standard histogram plotting."""
    required_cols = [
        "stimType",
        "onsetLatency_ms",
        "TTLLatency_ms",
        "type",
        "source_file",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_cols)
        )

    lag_df = df.copy()

    lag_df["stimType"] = (
        lag_df["stimType"]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"auditory": "audio"})
    )

    lag_df["type"] = (
        lag_df["type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    lag_df["task"] = lag_df["source_file"].apply(extract_task_from_filename)

    lag_df = lag_df.loc[lag_df["stimType"].isin(["audio", "visual"])].copy()

    lag_df["onsetLatency_ms"] = pd.to_numeric(
        lag_df["onsetLatency_ms"], errors="coerce"
    )
    lag_df["TTLLatency_ms"] = pd.to_numeric(
        lag_df["TTLLatency_ms"], errors="coerce"
    )

    lag_df = lag_df.dropna(
        subset=["onsetLatency_ms", "TTLLatency_ms", "task"]
    ).copy()

    lag_df["lag_ms"] = (
        lag_df["onsetLatency_ms"] - lag_df["TTLLatency_ms"]
    )

    return lag_df


def prepare_lag_data_ptb(df):
    """Prepare lag data for old PTB files."""
    required_cols = ["latency", "type", "source_file"]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_cols)
        )

    rows = []

    for source_file in sorted(df["source_file"].unique()):
        file_df = df.loc[df["source_file"] == source_file].copy()
        file_df["type"] = file_df["type"].astype(str).str.strip()
        file_df["latency"] = pd.to_numeric(
            file_df["latency"], errors="coerce"
        )
        file_df = file_df.dropna(subset=["latency"]).reset_index(drop=True)

        if "_prod_" in source_file.lower():
            task = "prod"
        elif "_ntfd_" in source_file.lower():
            task = "ntfd"
        else:
            continue

        for idx in range(len(file_df) - 1):
            curr_type = file_df.loc[idx, "type"]
            next_type = file_df.loc[idx + 1, "type"]

            if (
                curr_type == "Response Event"
                and next_type == "Feedback Onset"
            ):
                response_latency = file_df.loc[idx, "latency"]
                feedback_latency = file_df.loc[idx + 1, "latency"]

                rows.append(
                    {
                        "source_file": source_file,
                        "stimType": "audio",
                        "type": "decision",
                        "task": task,
                        "lag_ms": feedback_latency - response_latency,
                    }
                )

    return pd.DataFrame(rows)


def prepare_lag_data_ptb_buf(df):
    """Prepare lag data for PTB buffer files."""
    required_cols = ["latency", "markerLabel", "source_file"]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_cols)
        )

    rows = []

    for source_file in sorted(df["source_file"].unique()):
        file_df = df.loc[df["source_file"] == source_file].copy()
        file_df["markerLabel"] = (
            file_df["markerLabel"].astype(str).str.strip().str.lower()
        )
        file_df["latency"] = pd.to_numeric(
            file_df["latency"], errors="coerce"
        )
        file_df = file_df.dropna(subset=["latency"]).reset_index(drop=True)

        task = extract_task_from_filename(source_file)
        buffer_tag = extract_buffer_from_filename(source_file)

        if task not in ["prod", "ntfd"] or buffer_tag is None:
            continue

        for idx in range(len(file_df) - 1):
            curr_label = file_df.loc[idx, "markerLabel"]
            next_label = file_df.loc[idx + 1, "markerLabel"]

            if curr_label == "ttl" and next_label == "sensor":
                ttl_latency = file_df.loc[idx, "latency"]
                sensor_latency = file_df.loc[idx + 1, "latency"]

                rows.append(
                    {
                        "source_file": source_file,
                        "stimType": "audio",
                        "type": "decision",
                        "task": task,
                        "buffer": buffer_tag,
                        "lag_ms": sensor_latency - ttl_latency,
                    }
                )

    return pd.DataFrame(rows)


def prepare_lag_data_st_curated(df):
    """Prepare lag data from curated ST parser output."""
    required_cols = [
        "task",
        "subject",
        "modality",
        "condition",
        "trial",
        "measurement",
        "onset",
        "event_type",
        "stimulus_type",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_cols)
        )

    st_df = df.copy()

    st_df["task"] = st_df["task"].astype(str).str.strip().str.lower()
    st_df["modality"] = st_df["modality"].astype(str).str.strip().str.lower()
    st_df["event_type"] = st_df["event_type"].astype(str).str.strip()
    st_df["stimulus_type"] = (
        st_df["stimulus_type"].astype(str).str.strip().str.lower()
    )
    st_df["onset"] = pd.to_numeric(st_df["onset"], errors="coerce")

    if "source_file" in st_df.columns:
        st_df["buffer"] = st_df["source_file"].apply(
            extract_buffer_from_filename
        )
    else:
        st_df["buffer"] = None

    st_df = st_df.dropna(subset=["onset"]).copy()
    st_df = st_df.loc[st_df["modality"].isin(["audio", "visual"])].copy()

    group_cols = [
        "task",
        "subject",
        "modality",
        "condition",
        "trial",
        "measurement",
        "stimulus_type",
        "buffer",
    ]

    rows = []

    for _, grp in st_df.groupby(group_cols, sort=False, dropna=False):
        grp = grp.reset_index(drop=True)

        for idx in range(1, len(grp)):
            curr_event = grp.loc[idx, "event_type"]
            prev_event = grp.loc[idx - 1, "event_type"]
            modality = grp.loc[idx, "modality"]

            prev_onset = grp.loc[idx - 1, "onset"]
            curr_onset = grp.loc[idx, "onset"]

            if modality == "audio":
                valid_pair = (
                    (curr_event == "Tone Onset" and prev_event == "TTL")
                    or (curr_event == "sensor" and prev_event == "TTL")
                )
            elif modality == "visual":
                valid_pair = (
                    curr_event == "Visual&TTL Onset"
                    and prev_event == "TTL Onset"
                )
            else:
                valid_pair = False

            if valid_pair:
                rows.append(
                    {
                        "stimType": modality,
                        "type": grp.loc[idx, "stimulus_type"],
                        "task": (
                            "prod"
                            if grp.loc[idx, "task"] == "production"
                            else (
                                "percep"
                                if grp.loc[idx, "task"] == "perception"
                                else grp.loc[idx, "task"]
                            )
                        ),
                        "buffer": grp.loc[idx, "buffer"],
                        "lag_ms": curr_onset - prev_onset,
                    }
                )

    return pd.DataFrame(rows)


def plot_lag_histograms(lag_df, output_dir, plot_title, out_name,
                        session_tag):
    """Plot lag histograms for audio and visual conditions."""
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

    colors = {"audio": "mediumseagreen", "visual": "gold"}

    for i, (ax, stim_type, title) in enumerate(zip(
        axes,
        ["audio", "visual"],
        ["Audio", "Visual"],
    )):
        subset = lag_df.loc[lag_df["stimType"] == stim_type, "lag_ms"]

        mean_val = subset.mean()
        sd_val = subset.std()
        median_val = subset.median()

        ax.hist(
            subset,
            bins=30,
            color=colors[stim_type],
            edgecolor="black",
            linewidth=0.5,
        )

        ax.axvline(
            median_val,
            linestyle="--",
            linewidth=1.5,
            color="black",
        )

        xmin, xmax = ax.get_xlim()
        x_offset = 0.035 * (xmax - xmin)

        ax.text(
            median_val + x_offset,
            0.95,
            f"Median = {median_val:.2f} ms",
            transform=ax.get_xaxis_transform(),
            va="top",
            ha="left",
        )

        ax.text(
            0.02,
            0.95,
            f"Mean = {mean_val:.2f} ms\nSD = {sd_val:.2f} ms",
            transform=ax.transAxes,
            va="top",
            ha="left",
            bbox=dict(
                boxstyle="round",
                facecolor="white",
                edgecolor="black",
                linewidth=0.5,
            ),
        )

        ax.set_title(title)
        ax.set_xlabel("Lag (ms)")

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if i == 1:
            ax.spines["left"].set_visible(False)
            ax.tick_params(left=False, labelleft=False)

    axes[0].set_ylabel("Count")

    fig.suptitle(plot_title)
    fig.tight_layout()

    out_file = os.path.join(
        output_dir, f"{out_name}_{session_tag}.png"
    )
    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_lag_histogram_single(lag_df, output_dir, plot_title, out_name,
                              session_tag):
    """Plot a single histogram for one condition."""
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(5, 4))

    subset = lag_df["lag_ms"]

    mean_val = subset.mean()
    sd_val = subset.std()
    median_val = subset.median()

    ax.hist(
        subset,
        bins=30,
        color="mediumseagreen",
        edgecolor="black",
        linewidth=0.5,
    )

    ax.axvline(
        median_val,
        linestyle="--",
        linewidth=1.5,
        color="black",
    )

    xmin, xmax = ax.get_xlim()
    x_offset = 0.035 * (xmax - xmin)

    ax.text(
        median_val + x_offset,
        0.95,
        f"Median = {median_val:.2f} ms",
        transform=ax.get_xaxis_transform(),
        va="top",
        ha="left",
    )

    ax.text(
        0.02,
        0.95,
        f"Mean = {mean_val:.2f} ms\nSD = {sd_val:.2f} ms",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor="black",
            linewidth=0.5,
        ),
    )

    ax.set_title("Audio")
    ax.set_xlabel("Lag (ms)")
    ax.set_ylabel("Count")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle(plot_title)
    fig.tight_layout()

    out_file = os.path.join(
        output_dir, f"{out_name}_{session_tag}.png"
    )
    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)


def ptb_filename_filter(filename):
    """Keep only PTB files."""
    name = filename.lower()
    return (
        name.endswith("_ptb.tsv")
        or ("_ptb_" in name and name.endswith(".tsv"))
    )


def st_buf_filename_filter(filename):
    """Keep only sequence long ST buffer files."""
    name = filename.lower()
    return (
        name.startswith("sequence_long_st_")
        and "buf-" in name
        and name.endswith(".tsv")
    )


# =====================================================================
# Inputs
# =====================================================================
home_dir = os.path.expanduser("~")
script_dir = os.path.dirname(os.path.abspath(__file__))

session_name = "psychopy_ptb_buf"  # Change this to select the session

session_configs = {
    "expy2": {
        "session_tag": "expy2",
        "output_subdir": "expy2",
        "input_dir": os.path.join(script_dir, "data_expy2_july2025"),
        "parser": "standard",
    },
    "psychopy": {
        "session_tag": "psychopy",
        "output_subdir": "psychopy",
        "input_dir": os.path.join(script_dir, "data_psychopy_nov2025"),
        "parser": "standard",
    },
    "psychopy_ptb": {
        "session_tag": "psychopy_ptb-st",
        "output_subdir": "psychopy_ptb",
        "input_dir": os.path.join(
            script_dir, "data_psychopy_ptb-st_feb2026"
        ),
        "parser": "ptb",
    },
    "psychopy_ptb_buf": {
        "session_tag": "psychopy_ptb-st_buf",
        "output_subdir": "psychopy_ptb_buf",
        "input_dir": os.path.join(
            script_dir, "data_psychopy_ptb-st_audio-only_april2026"
        ),
        "parser": "ptb_buf",
    },
    "psychopy_st": {
        "session_tag": "psychopy_ptb-st",
        "output_subdir": "psychopy_st",
        "input_file": os.path.join(
            script_dir,
            "curated_data_feb2026",
            "sequence_long_st.tsv",
        ),
        "parser": "st_curated",
    },
    "psychopy_st_buf": {
        "session_tag": "psychopy_ptb-st_buf",
        "output_subdir": "psychopy_st_buf",
        "input_dir": os.path.join(
            script_dir, "curated_data_april2026"
        ),
        "parser": "st_curated_buf",
    },
}

session_tag = session_configs[session_name]["session_tag"]
output_subdir = session_configs[session_name]["output_subdir"]
parser_type = session_configs[session_name]["parser"]

if parser_type in ["standard", "ptb", "ptb_buf", "st_curated_buf"]:
    input_dir = session_configs[session_name]["input_dir"]

if parser_type == "st_curated":
    input_file = session_configs[session_name]["input_file"]

theoretical_dir = os.path.join(script_dir, "theoretical_durations")

# No subfolder for expy2 and psychopy
if session_name in ["expy2", "psychopy"]:
    output_dir = os.path.join(script_dir, "lag_plots", session_tag)
else:
    output_dir = os.path.join(
        script_dir, "lag_plots", session_tag, output_subdir
    )

# =====================================================================
# Run
# =====================================================================
if __name__ == "__main__":

    if parser_type == "standard":
        all_data = load_tsv_files(input_dir)
        lag_data = prepare_lag_data(all_data)

        plot_lag_histograms(
            lag_data,
            output_dir,
            plot_title="Distribution of lags",
            out_name="lag_histograms_audio_visual",
            session_tag=session_name,
        )

        non_percep_data = lag_data.loc[
            lag_data["task"].isin(["prod", "ntfd"])
        ].copy()

        encoding_data = non_percep_data.loc[
            non_percep_data["type"].isin(["encoding", "decision"])
        ].copy()
        if not encoding_data.empty:
            plot_lag_histograms(
                encoding_data,
                output_dir,
                plot_title="Distribution of encoding lags",
                out_name="lag_histograms_audio_visual_encoding",
                session_tag=session_name,
            )

        decision_data = non_percep_data.loc[
            non_percep_data["type"] == "rest"
        ].copy()
        if not decision_data.empty:
            plot_lag_histograms(
                decision_data,
                output_dir,
                plot_title="Distribution of decision lags",
                out_name="lag_histograms_audio_visual_decision",
                session_tag=session_name,
            )

        for task, task_label in zip(
            ["prod", "percep", "ntfd"],
            ["production", "perception", "ntfd"],
        ):
            task_data = lag_data.loc[lag_data["task"] == task].copy()

            if not task_data.empty:
                plot_lag_histograms(
                    task_data,
                    output_dir,
                    plot_title=f"Distribution of {task_label} lags",
                    out_name=f"lag_histograms_audio_visual_{task}",
                    session_tag=session_name,
                )

            if task == "percep":
                continue

            task_encoding = task_data.loc[
                task_data["type"].isin(["encoding", "decision"])
            ].copy()

            if not task_encoding.empty:
                plot_lag_histograms(
                    task_encoding,
                    output_dir,
                    plot_title=(
                        f"Distribution of {task_label} encoding lags"
                    ),
                    out_name=(
                        f"lag_histograms_audio_visual_"
                        f"encoding_{task}"
                    ),
                    session_tag=session_name,
                )

            task_decision = task_data.loc[
                task_data["type"] == "rest"
            ].copy()

            if not task_decision.empty:
                plot_lag_histograms(
                    task_decision,
                    output_dir,
                    plot_title=(
                        f"Distribution of {task_label} decision lags"
                    ),
                    out_name=(
                        f"lag_histograms_audio_visual_"
                        f"decision_{task}"
                    ),
                    session_tag=session_name,
                )

    elif parser_type == "ptb":
        all_data = load_tsv_files(
            input_dir,
            filename_filter=ptb_filename_filter,
        )
        lag_data = prepare_lag_data_ptb(all_data)

        if not lag_data.empty:
            plot_lag_histogram_single(
                lag_data,
                output_dir,
                plot_title="Distribution of decision lags",
                out_name="lag_histogram_audio_decision",
                session_tag=session_name,
            )

        for task, task_label in zip(
            ["prod", "ntfd"],
            ["production", "ntfd"],
        ):
            task_data = lag_data.loc[lag_data["task"] == task].copy()

            if not task_data.empty:
                plot_lag_histogram_single(
                    task_data,
                    output_dir,
                    plot_title=(
                        f"Distribution of {task_label} decision lags"
                    ),
                    out_name=f"lag_histogram_audio_decision_{task}",
                    session_tag=session_name,
                )

    elif parser_type == "ptb_buf":
        all_data = load_tsv_files(
            input_dir,
            filename_filter=ptb_filename_filter,
        )
        lag_data = prepare_lag_data_ptb_buf(all_data)

        for buffer_tag in ["buf-01", "buf-05", "buf-08"]:
            buffer_data = lag_data.loc[
                lag_data["buffer"] == buffer_tag
            ].copy()

            if not buffer_data.empty:
                plot_lag_histogram_single(
                    buffer_data,
                    output_dir,
                    plot_title=(
                        f"Distribution of decision lags ({buffer_tag})"
                    ),
                    out_name=(
                        f"lag_histogram_audio_decision_{buffer_tag}"
                    ),
                    session_tag=session_name,
                )

            for task, task_label in zip(
                ["prod", "ntfd"],
                ["production", "ntfd"],
            ):
                task_buffer_data = buffer_data.loc[
                    buffer_data["task"] == task
                ].copy()

                if not task_buffer_data.empty:
                    plot_lag_histogram_single(
                        task_buffer_data,
                        output_dir,
                        plot_title=(
                            "Distribution of "
                            f"{task_label} decision lags "
                            f"({buffer_tag})"
                        ),
                        out_name=(
                            "lag_histogram_audio_decision_"
                            f"{task}_{buffer_tag}"
                        ),
                        session_tag=session_name,
                    )

    elif parser_type == "st_curated":
        all_data = load_single_tsv(input_file)
        lag_data = prepare_lag_data_st_curated(all_data)

        plot_lag_histograms(
            lag_data,
            output_dir,
            plot_title="Distribution of lags",
            out_name="lag_histograms_audio_visual",
            session_tag=session_name,
        )

        non_percep_data = lag_data.loc[
            lag_data["task"].isin(["prod", "ntfd"])
        ].copy()

        encoding_data = non_percep_data.loc[
            non_percep_data["type"].isin(["encoding", "decision"])
        ].copy()
        if not encoding_data.empty:
            plot_lag_histograms(
                encoding_data,
                output_dir,
                plot_title="Distribution of encoding lags",
                out_name="lag_histograms_audio_visual_encoding",
                session_tag=session_name,
            )

        decision_data = non_percep_data.loc[
            non_percep_data["type"] == "rest"
        ].copy()
        if not decision_data.empty:
            plot_lag_histograms(
                decision_data,
                output_dir,
                plot_title="Distribution of decision lags",
                out_name="lag_histograms_audio_visual_decision",
                session_tag=session_name,
            )

        for task, task_label in zip(
            ["prod", "percep", "ntfd"],
            ["production", "perception", "ntfd"],
        ):
            task_data = lag_data.loc[lag_data["task"] == task].copy()

            if not task_data.empty:
                plot_lag_histograms(
                    task_data,
                    output_dir,
                    plot_title=f"Distribution of {task_label} lags",
                    out_name=f"lag_histograms_audio_visual_{task}",
                    session_tag=session_name,
                )

            if task == "percep":
                continue

            task_encoding = task_data.loc[
                task_data["type"].isin(["encoding", "decision"])
            ].copy()

            if not task_encoding.empty:
                plot_lag_histograms(
                    task_encoding,
                    output_dir,
                    plot_title=(
                        f"Distribution of {task_label} encoding lags"
                    ),
                    out_name=(
                        f"lag_histograms_audio_visual_"
                        f"encoding_{task}"
                    ),
                    session_tag=session_name,
                )

            task_decision = task_data.loc[
                task_data["type"] == "rest"
            ].copy()

            if not task_decision.empty:
                plot_lag_histograms(
                    task_decision,
                    output_dir,
                    plot_title=(
                        f"Distribution of {task_label} decision lags"
                    ),
                    out_name=(
                        f"lag_histograms_audio_visual_"
                        f"decision_{task}"
                    ),
                    session_tag=session_name,
                )

    elif parser_type == "st_curated_buf":
        all_data = load_tsv_files(
            input_dir,
            filename_filter=st_buf_filename_filter,
        )
        lag_data = prepare_lag_data_st_curated(all_data)

        for buffer_tag in ["buf-01", "buf-05", "buf-08"]:
            buffer_data = lag_data.loc[
                lag_data["buffer"] == buffer_tag
            ].copy()

            if not buffer_data.empty:
                plot_lag_histogram_single(
                    buffer_data,
                    output_dir,
                    plot_title=f"Distribution of lags ({buffer_tag})",
                    out_name=f"lag_histogram_audio_{buffer_tag}",
                    session_tag=session_name,
                )

            buffer_non_percep = buffer_data.loc[
                buffer_data["task"].isin(["prod", "ntfd"])
            ].copy()

            buffer_encoding = buffer_non_percep.loc[
                buffer_non_percep["type"].isin(["encoding", "decision"])
            ].copy()

            if not buffer_encoding.empty:
                plot_lag_histogram_single(
                    buffer_encoding,
                    output_dir,
                    plot_title=(
                        f"Distribution of encoding lags ({buffer_tag})"
                    ),
                    out_name=(
                        f"lag_histogram_audio_encoding_{buffer_tag}"
                    ),
                    session_tag=session_name,
                )

            buffer_decision = buffer_non_percep.loc[
                buffer_non_percep["type"] == "rest"
            ].copy()

            if not buffer_decision.empty:
                plot_lag_histogram_single(
                    buffer_decision,
                    output_dir,
                    plot_title=(
                        f"Distribution of decision lags ({buffer_tag})"
                    ),
                    out_name=(
                        f"lag_histogram_audio_decision_{buffer_tag}"
                    ),
                    session_tag=session_name,
                )

            for task, task_label in zip(
                ["prod", "percep", "ntfd"],
                ["production", "perception", "ntfd"],
            ):
                task_buffer_data = buffer_data.loc[
                    buffer_data["task"] == task
                ].copy()

                if not task_buffer_data.empty:
                    plot_lag_histogram_single(
                        task_buffer_data,
                        output_dir,
                        plot_title=(
                            f"Distribution of {task_label} lags "
                            f"({buffer_tag})"
                        ),
                        out_name=f"lag_histogram_audio_{task}_{buffer_tag}",
                        session_tag=session_name,
                    )

                if task == "percep":
                    continue

                task_buffer_encoding = task_buffer_data.loc[
                    task_buffer_data["type"].isin(
                        ["encoding", "decision"]
                    )
                ].copy()

                if not task_buffer_encoding.empty:
                    plot_lag_histogram_single(
                        task_buffer_encoding,
                        output_dir,
                        plot_title=(
                            f"Distribution of {task_label} "
                            f"encoding lags ({buffer_tag})"
                        ),
                        out_name=(
                            "lag_histogram_audio_encoding_"
                            f"{task}_{buffer_tag}"
                        ),
                        session_tag=session_name,
                    )

                task_buffer_decision = task_buffer_data.loc[
                    task_buffer_data["type"] == "rest"
                ].copy()

                if not task_buffer_decision.empty:
                    plot_lag_histogram_single(
                        task_buffer_decision,
                        output_dir,
                        plot_title=(
                            f"Distribution of {task_label} "
                            f"decision lags ({buffer_tag})"
                        ),
                        out_name=(
                            "lag_histogram_audio_decision_"
                            f"{task}_{buffer_tag}"
                        ),
                        session_tag=session_name,
                    )