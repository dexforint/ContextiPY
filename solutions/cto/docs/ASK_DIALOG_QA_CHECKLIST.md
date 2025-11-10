# Ask Dialog UI - Manual QA Checklist

## Overview
This checklist covers manual testing scenarios for the Ask Dialog UI implementation.

## Test Setup
1. Ensure PySide6 is installed
2. Start a QApplication instance
3. Create test questions using the Questions API

## 1. Widget Rendering Tests

### 1.1 Text Input Widget
- [ ] Text question renders as QLineEdit
- [ ] Placeholder text shows description if provided
- [ ] Tooltip shows description on hover
- [ ] User can type text freely
- [ ] Required indicator (*) appears for required fields

### 1.2 Numeric Spin Box Widget (Integer)
- [ ] Integer question with bounds renders as QSpinBox
- [ ] Minimum value (ge) is enforced
- [ ] Maximum value (le) is enforced
- [ ] User cannot enter values outside bounds via spin buttons
- [ ] Default value is set to minimum if ge is specified
- [ ] Manual text entry respects bounds

### 1.3 Numeric Spin Box Widget (Float)
- [ ] Float question with bounds renders as QDoubleSpinBox
- [ ] Decimal places are displayed (4 decimals)
- [ ] Minimum value (ge) is enforced
- [ ] Maximum value (le) is enforced
- [ ] Default value is set to minimum if ge is specified

### 1.4 Enum Combo Box Widget
- [ ] Enum question renders as QComboBox
- [ ] All enum values appear in dropdown
- [ ] Enum class prefix is removed from display (e.g., "Color.RED" → "RED")
- [ ] Empty option appears for non-required enum fields
- [ ] Default value is pre-selected if provided
- [ ] Selected value is correctly returned

### 1.5 Image File Picker Widget
- [ ] ImageQuery renders as text field + "Browse..." button
- [ ] Placeholder text indicates image selection
- [ ] Browse button opens file dialog
- [ ] File dialog filters by specified formats
- [ ] Selected file path appears in text field
- [ ] User can manually type file path
- [ ] "All files (*.*)" option is available in filter

## 2. Validation Tests

### 2.1 Required Field Validation
- [ ] OK button validates before accepting
- [ ] Required fields show error if left empty
- [ ] Error message: "This field is required"
- [ ] Error appears below the field in red text
- [ ] Dialog does not close if validation fails
- [ ] Multiple required field errors show simultaneously

### 2.2 Numeric Bounds Validation
- [ ] Values below ge show error: "Value must be >= X"
- [ ] Values above le show error: "Value must be <= X"
- [ ] Validation respects both ge and le simultaneously
- [ ] Error appears below the field in red text
- [ ] Valid values within bounds pass validation

### 2.3 Enum Validation
- [ ] Invalid enum values are rejected
- [ ] Error message lists valid options
- [ ] Both "EnumClass.MEMBER" and "MEMBER" formats are accepted
- [ ] Empty value passes for non-required enum fields

### 2.4 Optional Field Validation
- [ ] Optional fields can be left empty
- [ ] No error appears for empty optional fields
- [ ] Dialog accepts empty optional fields

### 2.5 Validation Error Clearing
- [ ] Previous validation errors are cleared when OK is clicked again
- [ ] Fixed fields no longer show errors
- [ ] Unfixed fields still show errors

## 3. User Interaction Tests

### 3.1 Dialog Display
- [ ] Dialog appears centered on screen
- [ ] Dialog is modal (blocks interaction with other windows)
- [ ] Window title is "Questions"
- [ ] Header text: "Please provide the following information:"
- [ ] Minimum width is 500 pixels

### 3.2 Scrolling
- [ ] Form area is scrollable for many questions
- [ ] Scroll area has no visible frame
- [ ] All questions are accessible via scrolling
- [ ] Buttons remain visible at bottom during scroll

### 3.3 Button Behavior
- [ ] Cancel button closes dialog without validation
- [ ] Cancel button returns None to caller
- [ ] OK button is the default button (activates on Enter)
- [ ] OK button validates before closing
- [ ] OK button returns answers dictionary to caller

### 3.4 Keyboard Navigation
- [ ] Tab key moves between fields in order
- [ ] Shift+Tab moves backwards
- [ ] Enter key activates OK button
- [ ] Escape key cancels dialog

### 3.5 Tooltips and Help Text
- [ ] Description appears as tooltip on field label
- [ ] Description appears as tooltip on input widget
- [ ] Tooltip appears on hover
- [ ] Long descriptions wrap properly

## 4. Default Values Tests

### 4.1 Text Defaults
- [ ] Default text appears in QLineEdit
- [ ] User can clear default and enter new text
- [ ] Empty string after clearing is treated as empty field

### 4.2 Numeric Defaults
- [ ] Default numeric value appears in spin box
- [ ] User can change default value
- [ ] Default respects min/max bounds

### 4.3 Enum Defaults
- [ ] Default enum value is pre-selected in combo box
- [ ] User can change to different enum value
- [ ] Default enum value is correctly serialized

### 4.4 Image Defaults
- [ ] Default image path appears in text field
- [ ] User can browse for different file
- [ ] User can clear default path

## 5. Answer Collection Tests

### 5.1 Answer Dictionary
- [ ] Returned dictionary contains all answered fields
- [ ] Empty optional fields are excluded from dictionary
- [ ] Field names match question names
- [ ] Values are in correct format (not serialized)

### 5.2 Data Types
- [ ] String values are returned as strings
- [ ] Integer values are returned as ints
- [ ] Float values are returned as floats
- [ ] Enum values are returned as enum strings
- [ ] Image paths are returned as strings

### 5.3 Cancellation
- [ ] Cancel returns None
- [ ] X button (close) returns None
- [ ] Escape key returns None
- [ ] No answers are processed on cancellation

## 6. Integration Tests

### 6.1 Ask API Integration
- [ ] Ask() function renders dialog
- [ ] Ask() returns Questions instance on success
- [ ] Ask() returns None on cancellation
- [ ] Questions instance has correct attribute values
- [ ] Validation in models.py processes answers correctly

### 6.2 QApplication Integration
- [ ] ask() requires QApplication to be running
- [ ] ask() raises RuntimeError if no QApplication
- [ ] Dialog is modal within application context
- [ ] Application continues after dialog closes

### 6.3 Schema Generation
- [ ] Questions.ui_schema() generates correct format
- [ ] All question types are supported
- [ ] All metadata fields are included
- [ ] Enum values are serialized correctly

## 7. Edge Cases

### 7.1 Empty Schema
- [ ] Empty question list shows only header and buttons
- [ ] OK button still works with empty schema
- [ ] Returns empty dictionary

### 7.2 Single Question
- [ ] Single question dialog displays correctly
- [ ] No scrolling needed
- [ ] Validation works for single question

### 7.3 Many Questions
- [ ] 20+ questions display in scrollable area
- [ ] All questions are accessible
- [ ] Validation works for all questions
- [ ] Performance is acceptable

### 7.4 Long Text
- [ ] Long question titles wrap appropriately
- [ ] Long descriptions in tooltips are readable
- [ ] Long validation errors wrap
- [ ] Long default values display correctly

### 7.5 Special Characters
- [ ] Unicode characters in text fields
- [ ] Special characters in file paths
- [ ] HTML-like text is escaped properly
- [ ] Quotes in text don't break UI

## 8. Error Handling

### 8.1 Missing PySide6
- [ ] ask() raises RuntimeError with clear message
- [ ] AskDialog() raises RuntimeError with clear message
- [ ] Error message: "PySide6 is not available"

### 8.2 Invalid Schema
- [ ] Missing required schema fields handled gracefully
- [ ] Unknown question kinds fall back to text input
- [ ] Malformed enum lists handled

### 8.3 File Picker Issues
- [ ] Cancel in file dialog doesn't error
- [ ] Invalid file path entered manually is caught by validation
- [ ] Non-existent default paths display without error

## 9. Visual Styling

### 9.1 Layout
- [ ] Consistent spacing between fields (12px)
- [ ] Form labels aligned consistently
- [ ] Buttons aligned to right
- [ ] Margins around dialog content (24px)

### 9.2 Validation Errors
- [ ] Error text is red
- [ ] Error text is smaller (11px)
- [ ] Error text wraps for long messages
- [ ] Errors appear directly below fields

### 9.3 Required Indicators
- [ ] Asterisk (*) appears after required field labels
- [ ] Asterisk is clearly visible
- [ ] No asterisk for optional fields

## 10. Async/Script Runner Integration

### 10.1 Script Invocation
- [ ] Ask() can be called from script runner context
- [ ] Script execution pauses waiting for user input
- [ ] Dialog shows while script waits
- [ ] Script continues after dialog closes

### 10.2 Timeout Handling
- [ ] Script timeout is independent of dialog wait time
- [ ] Long-running dialog doesn't trigger script timeout
- [ ] User has time to fill out complex forms

### 10.3 Cancellation Handling
- [ ] Script receives None when user cancels
- [ ] Script can handle None return gracefully
- [ ] No errors logged on cancellation

## Testing Notes

### Test Environment
- OS: _______________
- Python Version: _______________
- PySide6 Version: _______________
- Screen Resolution: _______________

### Tester Information
- Name: _______________
- Date: _______________
- Build/Commit: _______________

### Issues Found
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Additional Comments
_______________________________________________
_______________________________________________
_______________________________________________
