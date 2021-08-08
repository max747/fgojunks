package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"image"
	"image/jpeg"
	_ "image/png"
	"log"
	"os"
	"path/filepath"
	"runtime"
)

const (
	program = "jpeger"
	version = "0.2.0"
	logName = "jpeger.log"

	success = 0
	failure = 1

	jpegQuality = 90
)

var logger *log.Logger

func processZipItem(zf *zip.File) (*bytes.Buffer, error) {
	rc, err := zf.Open()
	if err != nil {
		return nil, err
	}
	defer rc.Close()

	im, format, err := image.Decode(rc)
	if err != nil {
		return nil, err
	}
	logger.Printf("    %s %v", format, im.Bounds())
	buf := new(bytes.Buffer)
	options := &jpeg.Options{Quality: jpegQuality}
	if err := jpeg.Encode(buf, im, options); err != nil {
		return nil, err
	}
	return buf, nil
}

func convertZipItems(srcPath, destPath string) error {
	r, err := zip.OpenReader(srcPath)
	if err != nil {
		return err
	}
	defer r.Close()

	zipbuf := new(bytes.Buffer)
	w := zip.NewWriter(zipbuf)

	for _, f := range r.File {
		logger.Printf("  %s\n", f.Name)
		buf, err := processZipItem(f)
		if err != nil {
			logger.Printf("processZipFile: %v\n", err)
			logger.Printf("skip processing %s\n", f.Name)
			continue
		}
		stem, _ := splitExt(f.Name)
		outputName := fmt.Sprintf("%s.jpg", stem)
		logger.Printf("  => %s\n", outputName)
		wf, err := w.Create(outputName)
		if err != nil {
			return err
		}
		if _, err := wf.Write(buf.Bytes()); err != nil {
			return err
		}
	}

	out, err := os.Create(destPath)
	if err != nil {
		return err
	}
	defer out.Close()

	w.Close() // zipbuf を読みだす前に終端処理が必要
	if _, err := out.Write(zipbuf.Bytes()); err != nil {
		return err
	}
	logger.Println("done!")
	return nil
}

func splitExt(src string) (stem, ext string) {
	ext = filepath.Ext(src)
	stem = src[:len(src)-len(ext)]
	return
}

func run() int {
	logFile, err := os.OpenFile(logName, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
		return failure
	}
	defer logFile.Close()

	logger = log.New(logFile, "", log.LstdFlags)
	logger.Printf("<<< %s %s %s/%s >>>\n", program, version, runtime.GOOS, runtime.GOARCH)
	logger.Printf("args: %v\n", os.Args)

	if len(os.Args) < 2 {
		logger.Println("too few arguments")
		return failure
	}

	srcPath := os.Args[1]
	stat, err := os.Stat(srcPath)
	if os.IsNotExist(err) {
		logger.Printf("%s: no such file or directory\n", srcPath)
		return failure
	}
	srcIsDir := stat.IsDir()
	srcStem, srcExt := splitExt(srcPath)
	logger.Printf("stem: %s, ext: %s, isdir: %v\n", srcStem, srcExt, srcIsDir)
	destPath := fmt.Sprintf("%s_jpeg%s", srcStem, srcExt)
	logger.Printf("dest: %s\n", destPath)

	if err := convertZipItems(srcPath, destPath); err != nil {
		logger.Printf("convertZipItems: %v\n", err)
		return failure
	}
	return success
}

func main() {
	os.Exit(run())
}
