package org.example.database;

import java.sql.*;
import java.util.*;
import java.util.stream.Collectors;

public class GenericDAO {
    private String tableName;
    private Connection connection;
    private List<String> columns;
    private String primaryKey;

    public GenericDAO(String tableName, Connection connection) throws SQLException {
        this.tableName = tableName;
        this.connection = connection;
        this.columns = getColumns();
        this.primaryKey = columns.get(0);
    }

    public List<String> getColumns() {
        List<String> columns = new ArrayList<>();
        String sql = "SELECT column_name FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position";
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.setString(1, tableName);
            ResultSet rs = stmt.executeQuery();
            while (rs.next()) {
                columns.add(rs.getString("column_name"));
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return columns;
    }

    public String getPrimaryKey() {
        return primaryKey;
    }

    public void create(Map<String, Object> values) {
        if (values.isEmpty()) return;

        String columnsStr = String.join(", ", values.keySet());
        String placeholders = values.keySet().stream().map(k -> "?").collect(Collectors.joining(", "));
        String sql = "INSERT INTO " + tableName + " (" + columnsStr + ") VALUES (" + placeholders + ")";

        try (PreparedStatement stmt = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            setPreparedStatementValues(stmt, values.values().toArray());
            stmt.executeUpdate();

            // Obține ID-ul generat (dacă există o coloană ID auto-increment)
            ResultSet generatedKeys = stmt.getGeneratedKeys();
            if (generatedKeys.next()) {
                int rowId = generatedKeys.getInt(1);
                logSync(tableName, rowId, "INSERT");  // Logare sincronizare
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }


    public List<String[]> read(Map<String, Object> filters) {
        List<String[]> data = new ArrayList<>();
        if (columns.isEmpty()) return data;

        String whereClause = filters.isEmpty() ? "" : " WHERE " + filters.keySet().stream()
                .map(col -> col + " = ?")
                .collect(Collectors.joining(" AND "));
        String sql = "SELECT * FROM " + tableName + whereClause;

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            setPreparedStatementValues(stmt, filters.values().toArray());
            ResultSet rs = stmt.executeQuery();
            while (rs.next()) {
                String[] row = new String[columns.size()];
                for (int i = 0; i < columns.size(); i++) {
                    row[i] = rs.getString(columns.get(i));
                }
                data.add(row);
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return data;
    }

    public void update(Map<String, Object> values, String whereClause, Object... whereParams) {
        if (values.isEmpty()) return;

        String setClause = values.keySet().stream()
                .map(column -> column + " = ?")
                .collect(Collectors.joining(", "));
        String sql = "UPDATE " + tableName + " SET " + setClause + " WHERE " + whereClause;

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            Object[] queryParams = mergeArrays(values.values().toArray(), whereParams);
            setPreparedStatementValues(stmt, queryParams);
            int affectedRows = stmt.executeUpdate();

            if (affectedRows > 0) {
                int rowId = (int) whereParams[0]; // Se presupune că primul parametru din where este ID-ul
                logSync(tableName, rowId, "UPDATE");  // Logare sincronizare
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }


    private Object[] mergeArrays(Object[] first, Object[] second) {
        Object[] merged = new Object[first.length + second.length];
        System.arraycopy(first, 0, merged, 0, first.length);
        System.arraycopy(second, 0, merged, first.length, second.length);
        return merged;
    }

    public void delete(String whereClause, Object... params) {
        String sql = "DELETE FROM " + tableName + " WHERE " + whereClause;
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            setPreparedStatementValues(stmt, params);
            int affectedRows = stmt.executeUpdate();

            if (affectedRows > 0) {
                int rowId = (int) params[0]; // Se presupune că primul parametru din where este ID-ul
                logSync(tableName, rowId, "DELETE");  // Logare sincronizare
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }


    private void setPreparedStatementValues(PreparedStatement stmt, Object... values) throws SQLException {
        for (int i = 0; i < values.length; i++) {
            if (values[i] instanceof Boolean) {
                stmt.setBoolean(i + 1, (Boolean) values[i]);
            } else if (values[i] instanceof Integer) {
                stmt.setInt(i + 1, (Integer) values[i]);
            } else if (values[i] instanceof String[]) {  // ARRAY de String
                String[] stringArray = (String[]) values[i];
                Array sqlArray = stmt.getConnection().createArrayOf("text", stringArray);
                stmt.setArray(i + 1, sqlArray);
            } else if (values[i] instanceof Integer[]) {  // ARRAY de Integer
                Integer[] intArray = (Integer[]) values[i];
                Array sqlArray = stmt.getConnection().createArrayOf("integer", intArray);
                stmt.setArray(i + 1, sqlArray);
            } else if (values[i] instanceof Object[]) {  // Tratare generală pentru alte tipuri de array-uri
                Object[] objArray = (Object[]) values[i];
                Array sqlArray = stmt.getConnection().createArrayOf("text", objArray);
                stmt.setArray(i + 1, sqlArray);
            } else {
                stmt.setObject(i + 1, values[i]);
            }
        }
    }

    public Object parseValue(String text, String columnName) {
        if (text.matches("^-?\\d+$")) {
            return Integer.parseInt(text);
        } else if (text.equalsIgnoreCase("true") || text.equalsIgnoreCase("false")) {
            return Boolean.parseBoolean(text);
        }
        return text;
    }


    public void logSync(String tableName, int rowId, String operation) {
        String sql = "INSERT INTO sync_log (table_name, row_id, operation, timestamp) VALUES (?, ?, ?, NOW())";
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.setString(1, tableName);
            stmt.setInt(2, rowId);
            stmt.setString(3, operation);
            stmt.executeUpdate();
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }


}