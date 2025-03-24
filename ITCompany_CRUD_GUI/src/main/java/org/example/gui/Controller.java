package org.example.gui;

import org.example.database.GenericDAO;
import javax.swing.*;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Controller {
    private GenericDAO dao;
    private Connection connection;
    private String currentTable;

    private JComboBox<String> tableSelector;
    private JTextField inputField;
    private JButton addButton, updateButton, deleteButton;

    public Controller(JComboBox<String> tableSelector, JTextField inputField, JButton addButton,
                      JButton updateButton, JButton deleteButton) {
        this.tableSelector = tableSelector;
        this.inputField = inputField;
        this.addButton = addButton;
        this.updateButton = updateButton;
        this.deleteButton = deleteButton;

        try {
            setupDatabase((String) tableSelector.getSelectedItem());
        } catch (SQLException e) {
            showError("Database connection error: " + e.getMessage());
        }

        tableSelector.addActionListener(e -> changeTable());
        addButton.addActionListener(e -> addEntry());
        updateButton.addActionListener(e -> updateEntry());
        deleteButton.addActionListener(e -> deleteEntry());
    }

    private void setupDatabase(String tableName) throws SQLException {
        if (connection == null) {
            connection = org.example.database.DatabaseConnector.getPostgresConnection();
        }
        this.dao = new GenericDAO(tableName, connection);
        this.currentTable = tableName;
    }

    private void changeTable() {
        try {
            String selectedTable = (String) tableSelector.getSelectedItem();
            if (selectedTable != null && !selectedTable.equals(currentTable)) {
                setupDatabase(selectedTable);
            }
        } catch (SQLException e) {
            showError("Error loading table: " + e.getMessage());
        }
    }

    private void addEntry() {
        if (dao == null) return;
        Map<String, Object> values = new HashMap<>();
        List<String> columns = dao.getColumns();

        for (String column : columns) {
            String inputValue = JOptionPane.showInputDialog("Enter value for " + column + ":");
            if (inputValue != null && !inputValue.trim().isEmpty()) {
                values.put(column, dao.parseValue(inputValue, column));
            }
        }
        dao.create(values);
    }

    private void updateEntry() {
        if (dao == null) return;
        String primaryKey = dao.getPrimaryKey();

        // Cerem ID-ul în mod interactiv
        String idValue = JOptionPane.showInputDialog("Enter " + primaryKey + " of entry to update:");
        if (idValue == null || idValue.trim().isEmpty()) return;

        Map<String, Object> values = new HashMap<>();
        List<String> columns = dao.getColumns();

        for (String column : columns) {
            if (!column.equals(primaryKey)) { // Nu modificăm primary key-ul
                String inputValue = JOptionPane.showInputDialog("Enter new value for " + column + " (leave empty to keep unchanged):");
                if (inputValue != null && !inputValue.trim().isEmpty()) {
                    values.put(column, dao.parseValue(inputValue, column));
                }
            }
        }

        if (!values.isEmpty()) {
            dao.update(values, primaryKey + " = ?", idValue);
        }
    }

    private void deleteEntry() {
        if (dao == null) return;
        String primaryKey = dao.getPrimaryKey();
        String idValue = JOptionPane.showInputDialog("Enter " + primaryKey + " of entry to delete:");
        if (idValue != null && !idValue.trim().isEmpty()) {
            dao.delete(primaryKey + " = ?", idValue);
        }
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(null, message, "Error", JOptionPane.ERROR_MESSAGE);
    }
}