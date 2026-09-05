package com.aiops.orderservice.controller;

import com.aiops.orderservice.dto.OrderRequest;
import com.aiops.orderservice.dto.OrderResponse;
import com.aiops.orderservice.model.Order;
import com.aiops.orderservice.service.OrderService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    // Entry point of the whole demo flow: place an order, which triggers
    // order-service -> payment-service -> notification-service
    // and
    // order-service -> inventory-service
    @PostMapping
    public ResponseEntity<OrderResponse> placeOrder(@RequestBody OrderRequest request) {
        OrderResponse response = orderService.placeOrder(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<Order> getOrder(@PathVariable String orderId) {
        Order order = orderService.getOrder(orderId);
        if (order == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(order);
    }
}
