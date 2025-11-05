# Field Day Crop Input Guide

## Overview

The Field Day API now supports multiple flexible formats for inputting crop information, allowing you to assign multiple crops to farmers in various ways. This guide explains all supported input formats and their use cases.

## Supported Input Formats

### Format 1: Individual Crop Entries (Recommended for precise control)

**Use Case**: When you want precise control over acreage for each crop.

```json
{
  "attendee_farmer_id": ["68", "68", "68"],
  "attendee_crop": ["rice", "wheat", "cotton"],
  "attendee_acreage": [2.0, 2.5, 1.5]
}
```

**Result**: Creates 3 separate attendance records for farmer 68:
- Rice: 2.0 acres
- Wheat: 2.5 acres  
- Cotton: 1.5 acres

### Format 2: Comma-Separated Crops (Convenient for equal distribution)

**Use Case**: When you want to assign multiple crops to a farmer with equal acreage distribution.

```json
{
  "attendee_farmer_id": ["68"],
  "attendee_crop": ["rice,wheat,cotton"],
  "attendee_acreage": [6.0]
}
```

**Result**: Creates 3 separate attendance records for farmer 68:
- Rice: 2.0 acres (6.0 ÷ 3)
- Wheat: 2.0 acres (6.0 ÷ 3)
- Cotton: 2.0 acres (6.0 ÷ 3)

### Format 3: Mixed Formats

**Use Case**: When you have different farmers with different crop input needs.

```json
{
  "attendee_farmer_id": ["68", "69"],
  "attendee_crop": ["rice,wheat", "cotton"],
  "attendee_acreage": [4.0, 2.0]
}
```

**Result**: 
- Farmer 68: Rice (2.0 acres) + Wheat (2.0 acres)
- Farmer 69: Cotton (2.0 acres)

## Complete API Example

```json
{
  "title": "Crop Demonstration Field Day",
  "date": "2024-01-15",
  "location": "Demo Farm Location",
  "total_participants": 2,
  "demonstrations_conducted": 3,
  "feedback": "Excellent participation and learning outcomes",
  "attendee_farmer_id": ["68", "69"],
  "attendee_crop": ["rice,wheat,cotton", "potato"],
  "attendee_acreage": [9.0, 3.0]
}
```

**Result**:
- Farmer 68: Rice (3.0 acres) + Wheat (3.0 acres) + Cotton (3.0 acres)
- Farmer 69: Potato (3.0 acres)

## Data Structure Details

### Input Fields

- **`attendee_farmer_id`**: Array of farmer IDs (can be repeated for multiple crops)
- **`attendee_crop`**: Array of crop names (supports comma-separated values)
- **`attendee_acreage`**: Array of acreage values (distributed among crops when comma-separated)

### Output Structure

Each crop creates:
1. **FieldDayAttendance** record with farmer information and primary crop
2. **FieldDayAttendanceCrop** record for detailed crop tracking

## Flexible Input Processing

The system uses `FlexibleListField` which accepts:
- **Arrays**: `["rice", "wheat"]`
- **Comma-separated strings**: `"rice,wheat"`
- **Mixed formats**: `["rice,wheat", "cotton"]`

## Best Practices

### 1. Use Format 1 for Precision
When you need different acreages for different crops:
```json
{
  "attendee_farmer_id": ["68", "68"],
  "attendee_crop": ["rice", "wheat"],
  "attendee_acreage": [3.5, 2.0]
}
```

### 2. Use Format 2 for Convenience
When crops have equal importance/acreage:
```json
{
  "attendee_farmer_id": ["68"],
  "attendee_crop": ["rice,wheat"],
  "attendee_acreage": [5.5]
}
```

### 3. Combine Formats as Needed
```json
{
  "attendee_farmer_id": ["68", "69", "69"],
  "attendee_crop": ["rice,wheat", "cotton", "potato"],
  "attendee_acreage": [4.0, 2.0, 1.5]
}
```

## Error Handling

The system gracefully handles:
- **Missing farmers**: Creates attendance with farmer name as "Unknown Farmer (ID)"
- **Mismatched array lengths**: Automatically expands shorter arrays
- **Empty crop strings**: Skips empty crop entries
- **Invalid acreage**: Defaults to 0.0

## Migration from Old Format

If you're migrating from the old single-crop format:

**Old Format**:
```json
{
  "attendee_farmer_id": ["68"],
  "attendee_crop": ["rice"],
  "attendee_acreage": [3.0]
}
```

**New Format (same result)**:
```json
{
  "attendee_farmer_id": ["68"],
  "attendee_crop": ["rice"],
  "attendee_acreage": [3.0]
}
```

**New Format (multiple crops)**:
```json
{
  "attendee_farmer_id": ["68"],
  "attendee_crop": ["rice,wheat"],
  "attendee_acreage": [6.0]
}
```

## Testing

Use the provided test scripts to verify functionality:
- `test_crop_separation.py`: Basic crop separation test
- `test_multiple_crops_single_farmer.py`: Comparison of both formats
- `test_comprehensive_crop_scenarios.py`: All scenarios test

## Support

For questions or issues with crop input formats, refer to the test scripts or contact the development team.