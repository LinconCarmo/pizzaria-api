def main():
    print("Hello from pizzaria-api!")


if __name__ == "__main__":
    main()



@app.get("/test-error")
async def test_error():
    raise NotFoundError("User not found")
