package com.aiops.paymentservice.controller;

import com.aiops.paymentservice.dto.PaymentRequest;
import com.aiops.paymentservice.dto.PaymentResponse;
import com.aiops.paymentservice.service.PaymentService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/payments")
public class PaymentController {

    private final PaymentService paymentService;

    public PaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @PostMapping
    public ResponseEntity<PaymentResponse> charge(@RequestBody PaymentRequest request) {
        PaymentResponse response = paymentService.charge(request);
        return ResponseEntity.ok(response);
    }
}
