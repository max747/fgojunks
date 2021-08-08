package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"image"
	"image/jpeg"
	_ "image/png"
	"io"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"golang.org/x/text/encoding/japanese"
)

const (
	program = "jpeger"
	version = "0.3.0"
	logName = "jpeger.log"

	success = 0
	failure = 1

	jpegQuality = 90
)

var logger *log.Logger

func processImage(data io.ReadCloser) (*bytes.Buffer, error) {
	im, format, err := image.Decode(data)
	if err != nil {
		return nil, fmt.Errorf("image.Decode: %w", err)
	}
	logger.Printf("    %s %v", format, im.Bounds())

	buf := new(bytes.Buffer)
	options := &jpeg.Options{Quality: jpegQuality}
	if err := jpeg.Encode(buf, im, options); err != nil {
		return nil, fmt.Errorf("jpeg.Encode: %w", err)
	}
	return buf, nil
}

func processImageFile(srcPath, destPath string) error {
	r, err := os.Open(srcPath)
	if err != nil {
		return fmt.Errorf("os.Open: %w", err)
	}
	defer r.Close()

	w, err := os.Create(destPath)
	if err != nil {
		return fmt.Errorf("os.Create: %w", err)
	}
	defer w.Close()

	buf, err := processImage(r)
	if err != nil {
		return fmt.Errorf("processImage: %w", err)
	}

	_, err = w.Write(buf.Bytes())
	if err != nil {
		return fmt.Errorf("w.Write: %w", err)
	}
	return nil
}

func processZipItem(zf *zip.File) (*bytes.Buffer, error) {
	rc, err := zf.Open()
	if err != nil {
		return nil, fmt.Errorf("zf.Open: %w", err)
	}
	defer rc.Close()

	buf, err := processImage(rc)
	if err != nil {
		return nil, fmt.Errorf("processImage: %w", err)
	}
	return buf, nil
}

func convertZipItems(srcPath, destPath string) error {
	r, err := zip.OpenReader(srcPath)
	if err != nil {
		return fmt.Errorf("zip.OpenReader: %w", err)
	}
	defer r.Close()

	zipbuf := new(bytes.Buffer)
	w := zip.NewWriter(zipbuf)

	for _, f := range r.File {
		logger.Printf("  %s\n", f.Name)
		buf, err := processZipItem(f)
		if err != nil {
			// エラーでも中断せずに継続する
			logger.Printf("processZipFile: %v\n", err)
			logger.Printf("skip processing %s\n", f.Name)
			continue
		}
		stem, _ := splitExt(f.Name)
		outputName := fmt.Sprintf("%s.jpg", stem)
		logger.Printf("  => %s\n", outputName)
		wf, err := w.Create(outputName)
		if err != nil {
			return fmt.Errorf("w.Create: %w", err)
		}
		if _, err := wf.Write(buf.Bytes()); err != nil {
			return fmt.Errorf("wf.Write: %w", err)
		}
	}

	out, err := os.Create(destPath)
	if err != nil {
		return fmt.Errorf("os.Create: %w", err)
	}
	defer out.Close()

	w.Close() // zipbuf を読みだす前に終端処理が必要
	if _, err := out.Write(zipbuf.Bytes()); err != nil {
		return fmt.Errorf("out.Write: %w", err)
	}
	return nil
}

func splitExt(src string) (stem, ext string) {
	ext = filepath.Ext(src)
	stem = src[:len(src)-len(ext)]
	return
}

func decodePathStrings(src string) (string, error) {
	switch runtime.GOOS {
	case "windows":
		decoder := japanese.ShiftJIS.NewDecoder()
		utf8str, err := decoder.String(src)
		if err != nil {
			return src, fmt.Errorf("decoder.String: %w", err)
		}
		return utf8str, nil
	default:
		return src, nil
	}
}

func resolveDestPath(srcPath string) string {
	srcStem, srcExt := splitExt(srcPath)
	switch strings.ToLower(srcExt) {
	case ".png":
		return fmt.Sprintf("%s.jpg", srcStem)

	case ".jpg", ".jpeg":
		return fmt.Sprintf("%s%s", srcStem, srcExt)

	default:
		return fmt.Sprintf("%s_jpeg%s", srcStem, srcExt)
	}
}

func copyFile(src, dest string) error {
	r, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("os.Open: %w", err)
	}
	defer r.Close()

	w, err := os.Create(dest)
	if err != nil {
		return fmt.Errorf("os.Create: %w", err)
	}
	defer w.Close()

	if _, err := io.Copy(w, r); err != nil {
		return fmt.Errorf("io.Copy: %w", err)
	}
	return nil
}

func runUnit(srcPath, destPath string, skipJpeg bool) error {
	_, srcExt := splitExt(srcPath)
	switch strings.ToLower(srcExt) {
	case ".png":
		if err := processImageFile(srcPath, destPath); err != nil {
			return fmt.Errorf("processImageFile: %w", err)
		}
	case ".jpg", ".jpeg":
		if skipJpeg {
			logger.Printf("skip processing jpeg file: %s\n", srcPath)
			return nil
		}

		if err := copyFile(srcPath, destPath); err != nil {
			return fmt.Errorf("copyFile: %w", err)
		}

	case ".zip":
		if err := convertZipItems(srcPath, destPath); err != nil {
			return fmt.Errorf("convertZipItems: %w", err)
		}
	default:
		return fmt.Errorf("unsupported file type: %s", srcExt)
	}
	return nil
}

func run() int {
	logFile, err := os.OpenFile(logName, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
		return failure
	}
	defer logFile.Close()
	multiWriter := io.MultiWriter(os.Stdout, logFile)

	logger = log.New(multiWriter, "", log.LstdFlags)
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

	destPath := resolveDestPath(srcPath)
	logger.Printf("dest: %s\n", destPath)

	if srcIsDir {
		logger.Printf("start to walk on: %s\n", srcPath)
		if err := filepath.Walk(srcPath, func(child string, info fs.FileInfo, err error) error {
			if err != nil {
				return fmt.Errorf("path %s; err: %w", child, err)
			}
			logger.Printf("  | %s\n", child)

			if info.IsDir() {
				destDir := strings.Replace(child, srcPath, destPath, 1)
				if err := os.Mkdir(destDir, os.ModeDir); err != nil {
					return fmt.Errorf("os.Mkdir: %w", err)
				}
				return nil
			}

			parent, childName := filepath.Split(child)
			destName := resolveDestPath(childName)
			destParent := strings.Replace(parent, srcPath, destPath, 1)
			dest := filepath.Join(destParent, destName)
			logger.Printf("  | dest: %s\n", dest)

			// jpeg は単にコピー
			if err := runUnit(child, dest, false); err != nil {
				logger.Printf("runUnit: %s\n", err)
				// 単発の処理でエラーが発生しても止めずに続行
			}
			return nil

		}); err != nil {
			logger.Printf("filePath.Walk: %s\n", err)
			return failure
		}

	} else {
		// jpeg は無視
		if err := runUnit(srcPath, destPath, true); err != nil {
			logger.Printf("runUnit: %s\n", err)
			return failure
		}
	}

	logger.Println("done!")
	return success
}

func main() {
	os.Exit(run())
}
