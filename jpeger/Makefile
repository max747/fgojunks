.PHONY: build windows clean

build:
	go build -o jpeger main.go

windows:
	docker run --rm -v "$(shell pwd)":/usr/src/myapp -w /usr/src/myapp -e GOOS=windows -e GOARCH=amd64 golang:1.16 go build -v -o jpeger.exe main.go

clean:
	rm -rvf jpeger*
