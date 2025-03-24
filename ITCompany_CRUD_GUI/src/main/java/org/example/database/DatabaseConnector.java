package org.example.database;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class DatabaseConnector {
    private static final String POSTGRES_URL = "jdbc:postgresql://localhost:5432/ITCompany_postgres";
    private static final String POSTGRES_USER = "admin";
    private static final String POSTGRES_PASSWORD = "Scotianu_2415";

    private static final String MYSQL_URL = "jdbc:mysql://localhost:3306/ITCompany_mySQL";
    private static final String MYSQL_USER = "admin";
    private static final String MYSQL_PASSWORD = "Scotianu_2415";

    public static Connection getPostgresConnection() throws SQLException {
        return DriverManager.getConnection(POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD);
    }

    public static Connection getMySQLConnection() throws SQLException {
        return DriverManager.getConnection(MYSQL_URL, MYSQL_USER, MYSQL_PASSWORD);
    }
}