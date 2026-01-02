# L5Kit Dataset Download Instructions

## Dataset Variant: L5Kit Sample Dataset (Mini)

This project uses the **L5Kit Sample Dataset** (mini variant) for Phase 0 validation and development. This variant is chosen because:

- **Demo-reliable**: Smaller size (~1-2 GB) makes it quick to download and validate
- **Lightweight**: Suitable for local development without requiring large storage
- **Complete structure**: Contains all necessary arrays (scenes, frames, agents) for validation
- **Stable format**: Well-documented zarr structure that matches the L5Kit standard

## Manual Download Steps

1. **Visit the Lyft Level 5 Dataset page**
   - Go to: https://level-5.global/data/
   - Navigate to the "Sample Dataset" or "L5Kit Sample" section

2. **Download the zarr dataset**
   - Look for the "sample_scenes.zarr" or similar zarr archive
   - Download the complete zarr directory structure
   - The dataset is typically provided as a tar.gz archive or as a directory structure

3. **Extract the dataset**
   ```bash
   # If downloaded as tar.gz
   tar -xzf sample_scenes.zarr.tar.gz
   
   # Or if provided as a directory, ensure it's extracted to your desired location
   ```

4. **Verify the directory structure**
   After extraction, you should have a directory structure like:
   ```
   sample_scenes.zarr/
   ├── scenes/          # Scene metadata array
   ├── frames/          # Frame-level data array
   ├── agents/          # Agent tracks array
   └── tl_faces/        # Traffic light faces (optional, not used in Phase 0)
   ```

## Expected Directory Structure

The zarr dataset should contain the following top-level arrays:

- **scenes/**: Scene metadata with fields:
  - `frame_index_interval`: Start and end frame indices for each scene
  - `host`: Host identifier
  - `start_time`: Scene start timestamp
  - `end_time`: Scene end timestamp

- **frames/**: Frame-level data with fields:
  - `timestamp`: Frame timestamp (nanoseconds)
  - `agent_index_interval`: Start and end agent indices for each frame
  - `traffic_light_faces_index_interval`: Traffic light indices (not used)

- **agents/**: Agent track data with fields:
  - `centroid`: Position [x, y, z] in meters
  - `velocity`: Velocity [vx, vy, vz] in m/s
  - `yaw`: Orientation in radians
  - `track_id`: Unique track identifier
  - `label_probabilities`: Classification probabilities (if present)

## Setting the Dataset Path

After downloading, set the dataset path in your environment or configuration:

```bash
export L5KIT_DATASET_PATH=/path/to/sample_scenes.zarr
```

Or create a `.env` file (copy from `.env.example`) and add:

```
L5KIT_DATASET_PATH=/path/to/sample_scenes.zarr
```

## Alternative: Using L5Kit Python Package

If you have the `l5kit` Python package installed, you can also use their dataset loader, but for Phase 0, we use direct zarr access to validate the raw dataset structure.

## Notes

- **No fragile download links**: This document describes the manual process to avoid broken links
- **Dataset location**: Store the dataset in a location accessible to your development environment
- **Permissions**: Ensure read permissions on the zarr directory
- **Validation**: After download, run `scripts/inspect_l5kit.py` to validate the dataset structure

