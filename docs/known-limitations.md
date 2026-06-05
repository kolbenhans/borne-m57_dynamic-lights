# Known Limitations

## Split Vial EEPROM synchronization

Dynamic lighting reads the active keymap from the local Vial dynamic keymap EEPROM of each half.

This means that after changing the layout in Vial, only the currently connected half immediately reflects the updated lighting.

### Workaround

1. Connect the master half via USB.
2. Change the layout in Vial.
3. Save the layout as a `.vil` file.
4. Connect the other half via USB.
5. Load the saved `.vil` file in Vial.
6. Reconnect the preferred master half.

After both halves have the same Vial layout stored, dynamic lighting works correctly on both sides.
