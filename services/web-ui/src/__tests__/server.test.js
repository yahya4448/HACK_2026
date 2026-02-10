const request = require("supertest");
const app = require("../server");

describe("API basics", () => {
  test("GET /health", async () => {
    const res = await request(app).get("/health");
    expect(res.statusCode).toBe(200);
    expect(res.body).toHaveProperty("status", "ok");
  });

  test("GET /metrics returns text", async () => {
    const res = await request(app).get("/metrics");
    expect(res.statusCode).toBe(200);
    expect(res.header["content-type"]).toMatch(/text\/plain/);
  });

  test("POST /api/v1/alerts creates incident", async () => {
    const res = await request(app).post("/api/v1/alerts").send({ service: "test", severity: "high", message: "it broke" });
    expect(res.statusCode).toBe(201);
    expect(res.body.data).toHaveProperty("id");
  });

  test("PUT acknowledge and resolve", async () => {
    const create = await request(app).post("/api/v1/alerts").send({ service: "t2", severity: "low" });
    const id = create.body.data.id;
    const ack = await request(app).put(`/api/v1/incidents/${id}/acknowledge`);
    expect(ack.statusCode).toBe(200);
    const res = await request(app).put(`/api/v1/incidents/${id}/resolve`);
    expect(res.statusCode).toBe(200);
  });
});
