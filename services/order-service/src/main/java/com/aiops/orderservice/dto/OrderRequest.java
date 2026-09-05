package com.aiops.orderservice.dto;

/** Body of POST /orders - what a client sends to place an order. */
public record OrderRequest(String customerId, String productId, int quantity, double amount) {
}
