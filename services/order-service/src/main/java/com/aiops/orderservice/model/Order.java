package com.aiops.orderservice.model;

import java.time.Instant;

/**
 * In-memory representation of an order. Phase 1 has no database - OrderService
 * keeps these in a ConcurrentHashMap. A real DB (or event log) arrives in a
 * later phase once Kafka is introduced.
 */
public class Order {

    private final String orderId;
    private final String traceId;
    private final String productId;
    private final int quantity;
    private final double amount;
    private final String customerId;
    private final Instant createdAt;
    private String status; // PENDING -> PAYMENT_CONFIRMED -> COMPLETED, or FAILED

    public Order(String orderId, String traceId, String productId, int quantity, double amount, String customerId) {
        this.orderId = orderId;
        this.traceId = traceId;
        this.productId = productId;
        this.quantity = quantity;
        this.amount = amount;
        this.customerId = customerId;
        this.createdAt = Instant.now();
        this.status = "PENDING";
    }

    public String getOrderId() {
        return orderId;
    }

    public String getTraceId() {
        return traceId;
    }

    public String getProductId() {
        return productId;
    }

    public int getQuantity() {
        return quantity;
    }

    public double getAmount() {
        return amount;
    }

    public String getCustomerId() {
        return customerId;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
