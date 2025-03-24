package org.example.gui;

import org.example.database.DatabaseConnector;
import org.example.database.GenericDAO;
import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class GUI extends JFrame {

    private JComboBox<String> tableSelector;
    private DefaultTableModel tableModel;
    private JTable tableView;
    private JPanel formPanel;
    private JTextField searchField;
    private GenericDAO dao; //todo modificat table name
    private static final String[] TABLES = {"employees", "clients", "projects"};

    public GUI() {
        setTitle("IT Company Database");
        setSize(800, 600);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        JPanel topPanel = new JPanel();
        tableSelector = new JComboBox<>(TABLES);
        topPanel.add(new JLabel("Table:"));
        topPanel.add(tableSelector);

        tableModel = new DefaultTableModel();
        tableView = new JTable(tableModel);
        JScrollPane scrollPanel = new JScrollPane(tableView);

        formPanel = new JPanel();
        formPanel.setLayout(new BoxLayout(formPanel, BoxLayout.Y_AXIS));

        add(topPanel, BorderLayout.NORTH);
        add(scrollPanel, BorderLayout.CENTER);
        add(formPanel, BorderLayout.SOUTH);

        tableSelector.addActionListener(e -> changeTable());

        try {
            setupDatabase(TABLES[0]);
        } catch (SQLException e) {
            showError("Database error: " + e.getMessage());
        }
    }

    private void setupDatabase(String tableName) throws SQLException {
        Connection conn = DatabaseConnector.getPostgresConnection();
        this.dao = new GenericDAO(tableName, conn);
        loadData();
        setupFormPanel();
    }

    private void changeTable() {
        try {
            String selectedTable = (String) tableSelector.getSelectedItem();
            if (selectedTable != null) {
                setupDatabase(selectedTable);
            }
        } catch (SQLException e) {
            showError("Error loading table: " + e.getMessage());
        }
    }

    private void loadData() {
        if (dao != null) {
            tableModel.setRowCount(0);
            tableModel.setColumnCount(0);

            List<String> columns = dao.getColumns();
            for (String column : columns) {
                tableModel.addColumn(column);
            }

            List<String[]> data = dao.read(new HashMap<>());
            for (String[] row : data) {
                tableModel.addRow(row);
            }
        }
    }

    private void setupFormPanel() {
        formPanel.removeAll();
        List<String> columns = dao.getColumns();
        if (columns.isEmpty()) return;

        // Add Entry Panel
        JPanel createPanel = new JPanel();
        createPanel.add(new JLabel("Add New Entry:"));
        JTextField[] createFields = new JTextField[columns.size()];
        for (int i = 0; i < columns.size(); i++) {
            createFields[i] = new JTextField(10);
            createPanel.add(new JLabel(columns.get(i) + ":"));
            createPanel.add(createFields[i]);
        }
        JButton createButton = new JButton("Add");
        createButton.addActionListener(e -> addEntry(createFields));
        createPanel.add(createButton);
        formPanel.add(createPanel);

        // Search Panel
        JPanel searchPanel = new JPanel();
        searchField = new JTextField(10);
        JButton searchButton = new JButton("Search");
        searchButton.addActionListener(e -> searchEntry());
        searchPanel.add(new JLabel("Search by Primary Key:"));
        searchPanel.add(searchField);
        searchPanel.add(searchButton);
        formPanel.add(searchPanel);

        // Update Panel
        JPanel updatePanel = new JPanel();
        updatePanel.add(new JLabel("Update Entry:"));

        JTextField updateIdField = new JTextField(10);
        updatePanel.add(new JLabel("Primary Key:"));
        updatePanel.add(updateIdField);

        JTextField[] updateFields = new JTextField[columns.size() - 1]; // Excludem primary key-ul
        for (int i = 1; i < columns.size(); i++) { // Începem de la index 1
            updateFields[i - 1] = new JTextField(10);
            updatePanel.add(new JLabel(columns.get(i) + ":"));
            updatePanel.add(updateFields[i - 1]);
        }

        JButton updateButton = new JButton("Update");
        updateButton.addActionListener(e -> updateEntry(updateIdField, updateFields));
        updatePanel.add(updateButton);
        formPanel.add(updatePanel);

        // Delete Panel
        JPanel deletePanel = new JPanel();
        JTextField deleteIdField = new JTextField(10);
        JButton deleteButton = new JButton("Delete");
        deleteButton.addActionListener(e -> deleteEntry(deleteIdField));
        deletePanel.add(new JLabel("Primary Key:"));
        deletePanel.add(deleteIdField);
        deletePanel.add(deleteButton);
        formPanel.add(deletePanel);

        formPanel.revalidate();
        formPanel.repaint();
    }

    private void addEntry(JTextField[] fields) {
        if (dao == null) return;
        Map<String, Object> values = new HashMap<>();
        List<String> columns = dao.getColumns();
        for (int i = 0; i < columns.size(); i++) {
            values.put(columns.get(i), dao.parseValue(fields[i].getText(), columns.get(i)));
        }
        dao.create(values);
        loadData();
    }

    private void updateEntry(JTextField idField, JTextField[] fields) {
        if (dao == null) return;
        String primaryKey = dao.getPrimaryKey();
        String idValue = idField.getText().trim();
        if (idValue.isEmpty()) return;

        Map<String, Object> values = new HashMap<>();
        List<String> columns = dao.getColumns();
        for (int i = 1; i < columns.size(); i++) {
            String inputValue = fields[i - 1].getText().trim();
            if (!inputValue.isEmpty()) {
                values.put(columns.get(i), dao.parseValue(inputValue, columns.get(i)));
            }
        }
        if (!values.isEmpty()) {
            dao.update(values, primaryKey + " = ?", new Object[]{Integer.parseInt(idValue)});
            loadData();
        }
    }

    private void deleteEntry(JTextField idField) {
        if (dao == null) return;
        String primaryKey = dao.getPrimaryKey();
        String idValue = idField.getText().trim();
        if (!idValue.isEmpty()) {
            dao.delete(primaryKey + " = ?", new Object[]{Integer.parseInt(idValue)});
            loadData();
        }
    }

    private void searchEntry() {
        if (dao == null) return;
        String keyword = searchField.getText().trim();
        if (keyword.isEmpty()) return;

        Map<String, Object> filters = new HashMap<>();
        filters.put(dao.getPrimaryKey(), Integer.parseInt(keyword));
        List<String[]> results = dao.read(filters);
        tableModel.setRowCount(0);
        for (String[] row : results) {
            tableModel.addRow(row);
        }
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(this, message, "Error", JOptionPane.ERROR_MESSAGE);
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new GUI().setVisible(true));
    }
}
