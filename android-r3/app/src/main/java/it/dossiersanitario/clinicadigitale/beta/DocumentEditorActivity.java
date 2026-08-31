package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PointF;
import android.graphics.RectF;
import android.media.ExifInterface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.opencv.android.OpenCVLoader;
import org.opencv.android.Utils;
import org.opencv.calib3d.Calib3d;
import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.Point;
import org.opencv.core.Scalar;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public final class DocumentEditorActivity extends Activity {
    public static final String EXTRA_SOURCE_PATH = "source_path";
    public static final String EXTRA_REPLACE_PATH = "replace_path";
    public static final String EXTRA_NEW_CAPTURE = "new_capture";

    private static final int GREEN = Color.rgb(23, 138, 114);
    private static final int GREEN_DARK = Color.rgb(19, 110, 93);

    private File sourceFile;
    private String replacePath;
    private boolean newCapture;
    private Bitmap originalBitmap;
    private Bitmap currentBitmap;
    private DocumentView documentView;
    private TextView status;
    private boolean openCvReady;
    private boolean completed;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(GREEN_DARK);
        getWindow().setNavigationBarColor(Color.BLACK);

        String source = getIntent().getStringExtra(EXTRA_SOURCE_PATH);
        replacePath = getIntent().getStringExtra(EXTRA_REPLACE_PATH);
        newCapture = getIntent().getBooleanExtra(EXTRA_NEW_CAPTURE, false);
        if (source == null || source.trim().isEmpty()) {
            failAndFinish("Documento non disponibile");
            return;
        }

        sourceFile = new File(source);
        if (!sourceFile.isFile()) {
            failAndFinish("Documento non disponibile");
            return;
        }

        openCvReady = OpenCVLoader.initLocal();
        originalBitmap = loadOrientedBitmap(sourceFile, 3200);
        if (originalBitmap == null) {
            failAndFinish("Immagine non leggibile");
            return;
        }
        currentBitmap = originalBitmap.copy(Bitmap.Config.ARGB_8888, true);
        setContentView(buildUi());
        documentView.setBitmap(currentBitmap);
        if (openCvReady) autoDetectEdges(false);
        else status.setText("OpenCV non inizializzato: rotazione e ritaglio manuale restano disponibili.");
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(18, 20, 20));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(14), dp(10), dp(14), dp(9));
        header.setBackgroundColor(GREEN_DARK);
        TextView title = label("Modifica documento", 20, Color.WHITE, true);
        TextView help = label("Trascina i quattro punti verdi sugli angoli del foglio. Puoi correggere orientamento, ritaglio, prospettiva e distorsione prima di salvare.", 12, Color.WHITE, false);
        help.setPadding(0, dp(4), 0, 0);
        header.addView(title);
        header.addView(help);
        root.addView(header);

        documentView = new DocumentView();
        root.addView(documentView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        status = label("", 12, Color.rgb(220, 228, 225), false);
        status.setPadding(dp(12), dp(7), dp(12), dp(5));
        root.addView(status);

        HorizontalScrollView toolsScroll = new HorizontalScrollView(this);
        toolsScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.HORIZONTAL);
        tools.setPadding(dp(8), dp(5), dp(8), dp(7));
        tools.setBackgroundColor(Color.rgb(32, 36, 35));

        tools.addView(toolButton("Auto bordi", v -> autoDetectEdges(true)));
        tools.addView(toolButton("Ruota ↺", v -> rotate(-90)));
        tools.addView(toolButton("Ruota ↻", v -> rotate(90)));
        tools.addView(toolButton("Ritaglia", v -> cropToCorners()));
        tools.addView(toolButton("Prospettiva", v -> applyPerspective()));
        tools.addView(toolButton("Barilotto", v -> correctDistortion(-0.10)));
        tools.addView(toolButton("Cuscinetto", v -> correctDistortion(0.10)));
        tools.addView(toolButton("Migliora", v -> enhanceDocument()));
        tools.addView(toolButton("Ripristina", v -> restoreOriginal()));
        toolsScroll.addView(tools);
        root.addView(toolsScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)));

        LinearLayout bottom = new LinearLayout(this);
        bottom.setOrientation(LinearLayout.HORIZONTAL);
        bottom.setPadding(dp(10), dp(8), dp(10), dp(10));
        bottom.setBackgroundColor(Color.rgb(245, 247, 246));

        Button cancel = actionButton("Annulla", false);
        cancel.setOnClickListener(v -> confirmCancel());
        bottom.addView(cancel, new LinearLayout.LayoutParams(0, dp(48), 1f));

        Button save = actionButton("Salva nel Dossier", true);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(0, dp(48), 1.45f);
        sp.setMargins(dp(8), 0, 0, 0);
        save.setOnClickListener(v -> saveDocument());
        bottom.addView(save, sp);
        root.addView(bottom);
        return root;
    }

    private Button toolButton(String text, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setBackgroundColor(Color.rgb(48, 54, 52));
        b.setPadding(dp(10), 0, dp(10), 0);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(44));
        p.setMargins(dp(4), 0, dp(4), 0);
        b.setLayoutParams(p);
        b.setOnClickListener(listener);
        return b;
    }

    private Button actionButton(String text, boolean primary) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setTextColor(primary ? Color.WHITE : Color.rgb(40, 52, 48));
        b.setBackgroundColor(primary ? GREEN : Color.rgb(224, 232, 229));
        return b;
    }

    private void rotate(int degrees) {
        Matrix m = new Matrix();
        m.postRotate(degrees);
        Bitmap rotated = Bitmap.createBitmap(currentBitmap, 0, 0, currentBitmap.getWidth(), currentBitmap.getHeight(), m, true);
        replaceCurrent(rotated, true);
        if (openCvReady) autoDetectEdges(false);
        status.setText(degrees > 0 ? "Documento ruotato a destra." : "Documento ruotato a sinistra.");
    }

    private void restoreOriginal() {
        Bitmap restored = originalBitmap.copy(Bitmap.Config.ARGB_8888, true);
        replaceCurrent(restored, true);
        if (openCvReady) autoDetectEdges(false);
        status.setText("Immagine originale ripristinata.");
    }

    private void autoDetectEdges(boolean notify) {
        if (!openCvReady) {
            if (notify) Toast.makeText(this, "Rilevamento automatico non disponibile", Toast.LENGTH_SHORT).show();
            return;
        }

        Mat src = new Mat();
        Mat gray = new Mat();
        Mat blurred = new Mat();
        Mat edges = new Mat();
        Mat hierarchy = new Mat();
        try {
            Utils.bitmapToMat(currentBitmap, src);
            Imgproc.cvtColor(src, gray, Imgproc.COLOR_RGBA2GRAY);
            Imgproc.GaussianBlur(gray, blurred, new Size(5, 5), 0);
            Imgproc.Canny(blurred, edges, 60, 180);

            List<MatOfPoint> contours = new ArrayList<>();
            Imgproc.findContours(edges, contours, hierarchy, Imgproc.RETR_LIST, Imgproc.CHAIN_APPROX_SIMPLE);
            double bestArea = 0;
            Point[] best = null;
            double imageArea = (double) currentBitmap.getWidth() * currentBitmap.getHeight();

            for (MatOfPoint contour : contours) {
                double area = Math.abs(Imgproc.contourArea(contour));
                if (area < imageArea * 0.12 || area <= bestArea) continue;
                MatOfPoint2f curve = new MatOfPoint2f(contour.toArray());
                double perimeter = Imgproc.arcLength(curve, true);
                MatOfPoint2f approx = new MatOfPoint2f();
                Imgproc.approxPolyDP(curve, approx, perimeter * 0.02, true);
                Point[] pts = approx.toArray();
                if (pts.length == 4) {
                    MatOfPoint convex = new MatOfPoint(pts);
                    if (Imgproc.isContourConvex(convex)) {
                        bestArea = area;
                        best = pts;
                    }
                    convex.release();
                }
                curve.release();
                approx.release();
            }

            if (best != null) {
                PointF[] ordered = orderCorners(best);
                documentView.setCorners(ordered);
                status.setText("Bordi rilevati. Trascina i punti se vuoi correggerli manualmente.");
            } else {
                documentView.resetCorners();
                status.setText("Bordi non rilevati con sufficiente sicurezza: regola manualmente i quattro punti.");
                if (notify) Toast.makeText(this, "Regola manualmente i quattro angoli", Toast.LENGTH_SHORT).show();
            }
        } catch (Exception e) {
            documentView.resetCorners();
            status.setText("Rilevamento automatico non riuscito: usa i punti manuali.");
        } finally {
            src.release(); gray.release(); blurred.release(); edges.release(); hierarchy.release();
        }
    }

    private void cropToCorners() {
        PointF[] p = documentView.getCorners();
        float minX = Float.MAX_VALUE, minY = Float.MAX_VALUE;
        float maxX = 0, maxY = 0;
        for (PointF q : p) {
            minX = Math.min(minX, q.x); minY = Math.min(minY, q.y);
            maxX = Math.max(maxX, q.x); maxY = Math.max(maxY, q.y);
        }
        int left = clamp(Math.round(minX), 0, currentBitmap.getWidth() - 2);
        int top = clamp(Math.round(minY), 0, currentBitmap.getHeight() - 2);
        int right = clamp(Math.round(maxX), left + 1, currentBitmap.getWidth());
        int bottom = clamp(Math.round(maxY), top + 1, currentBitmap.getHeight());
        Bitmap cropped = Bitmap.createBitmap(currentBitmap, left, top, right - left, bottom - top);
        replaceCurrent(cropped, true);
        status.setText("Ritaglio applicato.");
    }

    private void applyPerspective() {
        if (!openCvReady) {
            Toast.makeText(this, "Correzione prospettica non disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        PointF[] c = sortPointFs(documentView.getCorners());
        double widthA = distance(c[2], c[3]);
        double widthB = distance(c[1], c[0]);
        double heightA = distance(c[1], c[2]);
        double heightB = distance(c[0], c[3]);
        int outW = clamp((int) Math.round(Math.max(widthA, widthB)), 160, 3600);
        int outH = clamp((int) Math.round(Math.max(heightA, heightB)), 160, 3600);

        Mat src = new Mat();
        Mat dst = new Mat();
        Mat transform = null;
        MatOfPoint2f srcPts = new MatOfPoint2f(
                new Point(c[0].x, c[0].y), new Point(c[1].x, c[1].y),
                new Point(c[2].x, c[2].y), new Point(c[3].x, c[3].y));
        MatOfPoint2f dstPts = new MatOfPoint2f(
                new Point(0, 0), new Point(outW - 1, 0),
                new Point(outW - 1, outH - 1), new Point(0, outH - 1));
        try {
            Utils.bitmapToMat(currentBitmap, src);
            transform = Imgproc.getPerspectiveTransform(srcPts, dstPts);
            Imgproc.warpPerspective(src, dst, transform, new Size(outW, outH), Imgproc.INTER_CUBIC, Core.BORDER_REPLICATE, new Scalar(255, 255, 255, 255));
            Bitmap result = Bitmap.createBitmap(outW, outH, Bitmap.Config.ARGB_8888);
            Utils.matToBitmap(dst, result);
            replaceCurrent(result, true);
            status.setText("Prospettiva corretta e documento raddrizzato.");
        } catch (Exception e) {
            Toast.makeText(this, "Correzione prospettica non riuscita", Toast.LENGTH_SHORT).show();
        } finally {
            src.release(); dst.release(); srcPts.release(); dstPts.release();
            if (transform != null) transform.release();
        }
    }

    private void correctDistortion(double k1) {
        if (!openCvReady) {
            Toast.makeText(this, "Correzione distorsione non disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        Mat src = new Mat();
        Mat dst = new Mat();
        Mat camera = Mat.eye(3, 3, CvType.CV_64F);
        Mat dist = Mat.zeros(1, 5, CvType.CV_64F);
        try {
            Utils.bitmapToMat(currentBitmap, src);
            double f = Math.max(currentBitmap.getWidth(), currentBitmap.getHeight());
            camera.put(0, 0, f);
            camera.put(1, 1, f);
            camera.put(0, 2, currentBitmap.getWidth() / 2.0);
            camera.put(1, 2, currentBitmap.getHeight() / 2.0);
            dist.put(0, 0, k1, 0, 0, 0, 0);
            Calib3d.undistort(src, dst, camera, dist);
            Bitmap result = Bitmap.createBitmap(dst.cols(), dst.rows(), Bitmap.Config.ARGB_8888);
            Utils.matToBitmap(dst, result);
            replaceCurrent(result, true);
            status.setText(k1 < 0 ? "Correzione tipo barilotto applicata." : "Correzione tipo cuscinetto applicata.");
        } catch (Exception e) {
            Toast.makeText(this, "Correzione distorsione non riuscita", Toast.LENGTH_SHORT).show();
        } finally {
            src.release(); dst.release(); camera.release(); dist.release();
        }
    }

    private void enhanceDocument() {
        if (!openCvReady) {
            Toast.makeText(this, "Miglioramento automatico non disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        Mat src = new Mat();
        Mat rgb = new Mat();
        Mat blur = new Mat();
        Mat sharp = new Mat();
        Mat out = new Mat();
        try {
            Utils.bitmapToMat(currentBitmap, src);
            Imgproc.cvtColor(src, rgb, Imgproc.COLOR_RGBA2RGB);
            Imgproc.GaussianBlur(rgb, blur, new Size(0, 0), 2.2);
            Core.addWeighted(rgb, 1.32, blur, -0.32, 0, sharp);
            sharp.convertTo(sharp, -1, 1.08, -5);
            Imgproc.cvtColor(sharp, out, Imgproc.COLOR_RGB2RGBA);
            Bitmap result = Bitmap.createBitmap(out.cols(), out.rows(), Bitmap.Config.ARGB_8888);
            Utils.matToBitmap(out, result);
            replaceCurrent(result, false);
            status.setText("Contrasto e nitidezza migliorati.");
        } catch (Exception e) {
            Toast.makeText(this, "Miglioramento non riuscito", Toast.LENGTH_SHORT).show();
        } finally {
            src.release(); rgb.release(); blur.release(); sharp.release(); out.release();
        }
    }

    private void replaceCurrent(Bitmap next, boolean resetCorners) {
        if (next == null) return;
        if (currentBitmap != null && currentBitmap != originalBitmap && currentBitmap != next && !currentBitmap.isRecycled()) {
            currentBitmap.recycle();
        }
        currentBitmap = next.copy(Bitmap.Config.ARGB_8888, true);
        if (next != currentBitmap && next != originalBitmap && !next.isRecycled()) next.recycle();
        documentView.setBitmap(currentBitmap, resetCorners);
    }

    private void saveDocument() {
        if (currentBitmap == null) return;
        File target;
        if (replacePath != null && !replacePath.trim().isEmpty()) {
            target = new File(replacePath);
        } else {
            File dir = new File(getFilesDir(), "dossier_documents");
            if (!dir.exists() && !dir.mkdirs()) {
                Toast.makeText(this, "Impossibile preparare l'archivio", Toast.LENGTH_LONG).show();
                return;
            }
            target = new File(dir, "referto_foto_" + System.currentTimeMillis() + ".jpg");
        }

        File tmp = new File(target.getParentFile(), target.getName() + ".editing");
        try (FileOutputStream out = new FileOutputStream(tmp)) {
            if (!currentBitmap.compress(Bitmap.CompressFormat.JPEG, 94, out)) throw new IOException("compression failed");
            out.getFD().sync();
        } catch (IOException e) {
            tmp.delete();
            Toast.makeText(this, "Salvataggio non riuscito", Toast.LENGTH_LONG).show();
            return;
        }

        try {
            if (target.exists() && !target.delete()) throw new IOException("replace failed");
            if (!tmp.renameTo(target)) copyAndSync(tmp, target);
            tmp.delete();
            if (newCapture && sourceFile != null && !sourceFile.equals(target)) sourceFile.delete();
            completed = true;
            Intent result = new Intent();
            result.putExtra("saved_path", target.getAbsolutePath());
            setResult(RESULT_OK, result);
            finish();
        } catch (IOException e) {
            tmp.delete();
            Toast.makeText(this, "Salvataggio non riuscito", Toast.LENGTH_LONG).show();
        }
    }

    private void confirmCancel() {
        new AlertDialog.Builder(this)
                .setTitle("Annullare le modifiche?")
                .setMessage("Il documento non verrà salvato con le modifiche correnti.")
                .setNegativeButton("Continua a modificare", null)
                .setPositiveButton("Annulla modifiche", (d, w) -> cancelAndFinish())
                .show();
    }

    private void cancelAndFinish() {
        if (newCapture && sourceFile != null) sourceFile.delete();
        completed = true;
        setResult(RESULT_CANCELED);
        finish();
    }

    @Override public void onBackPressed() {
        confirmCancel();
    }

    @Override protected void onDestroy() {
        super.onDestroy();
        if (completed) {
            if (currentBitmap != null && currentBitmap != originalBitmap && !currentBitmap.isRecycled()) currentBitmap.recycle();
            if (originalBitmap != null && !originalBitmap.isRecycled()) originalBitmap.recycle();
        }
    }

    private void failAndFinish(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
        if (newCapture && sourceFile != null) sourceFile.delete();
        setResult(RESULT_CANCELED);
        finish();
    }

    private static Bitmap loadOrientedBitmap(File file, int maxDimension) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
        int sample = 1;
        while (Math.max(bounds.outWidth, bounds.outHeight) / sample > maxDimension * 2) sample *= 2;
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inSampleSize = sample;
        opts.inPreferredConfig = Bitmap.Config.ARGB_8888;
        Bitmap bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), opts);
        if (bitmap == null) return null;
        try {
            ExifInterface exif = new ExifInterface(file.getAbsolutePath());
            int orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            Matrix m = new Matrix();
            if (orientation == ExifInterface.ORIENTATION_ROTATE_90) m.postRotate(90);
            else if (orientation == ExifInterface.ORIENTATION_ROTATE_180) m.postRotate(180);
            else if (orientation == ExifInterface.ORIENTATION_ROTATE_270) m.postRotate(270);
            else return bitmap;
            Bitmap rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), m, true);
            if (rotated != bitmap) bitmap.recycle();
            return rotated;
        } catch (Exception ignored) {
            return bitmap;
        }
    }

    private static PointF[] orderCorners(Point[] pts) {
        PointF[] p = new PointF[4];
        for (int i = 0; i < 4; i++) p[i] = new PointF((float) pts[i].x, (float) pts[i].y);
        return sortPointFs(p);
    }

    private static PointF[] sortPointFs(PointF[] pts) {
        PointF tl = null, tr = null, br = null, bl = null;
        float minSum = Float.MAX_VALUE, maxSum = -Float.MAX_VALUE;
        float minDiff = Float.MAX_VALUE, maxDiff = -Float.MAX_VALUE;
        for (PointF p : pts) {
            float sum = p.x + p.y;
            float diff = p.x - p.y;
            if (sum < minSum) { minSum = sum; tl = p; }
            if (sum > maxSum) { maxSum = sum; br = p; }
            if (diff > maxDiff) { maxDiff = diff; tr = p; }
            if (diff < minDiff) { minDiff = diff; bl = p; }
        }
        return new PointF[]{new PointF(tl.x, tl.y), new PointF(tr.x, tr.y), new PointF(br.x, br.y), new PointF(bl.x, bl.y)};
    }

    private static double distance(PointF a, PointF b) {
        double dx = a.x - b.x, dy = a.y - b.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    private static int clamp(int v, int min, int max) {
        return Math.max(min, Math.min(max, v));
    }

    private static void copyAndSync(File source, File target) throws IOException {
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
    }

    private TextView label(String text, int sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(sp);
        v.setTextColor(color);
        if (bold) v.setTypeface(null, android.graphics.Typeface.BOLD);
        v.setLineSpacing(0, 1.1f);
        return v;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private final class DocumentView extends View {
        private final Paint border = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint handle = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint shade = new Paint(Paint.ANTI_ALIAS_FLAG);
        private Bitmap bitmap;
        private final PointF[] corners = new PointF[]{new PointF(), new PointF(), new PointF(), new PointF()};
        private final RectF imageRect = new RectF();
        private int activeCorner = -1;

        DocumentView() {
            super(DocumentEditorActivity.this);
            setBackgroundColor(Color.rgb(14, 16, 16));
            border.setStyle(Paint.Style.STROKE);
            border.setStrokeWidth(dp(3));
            border.setColor(Color.rgb(65, 225, 167));
            handle.setStyle(Paint.Style.FILL);
            handle.setColor(Color.rgb(65, 225, 167));
            shade.setColor(Color.argb(90, 0, 0, 0));
        }

        void setBitmap(Bitmap bitmap) {
            setBitmap(bitmap, true);
        }

        void setBitmap(Bitmap bitmap, boolean reset) {
            this.bitmap = bitmap;
            if (reset) resetCorners();
            invalidate();
        }

        void resetCorners() {
            if (bitmap == null) return;
            float ix = bitmap.getWidth() * 0.04f;
            float iy = bitmap.getHeight() * 0.04f;
            corners[0].set(ix, iy);
            corners[1].set(bitmap.getWidth() - ix, iy);
            corners[2].set(bitmap.getWidth() - ix, bitmap.getHeight() - iy);
            corners[3].set(ix, bitmap.getHeight() - iy);
            invalidate();
        }

        void setCorners(PointF[] points) {
            if (points == null || points.length != 4) return;
            for (int i = 0; i < 4; i++) corners[i].set(points[i].x, points[i].y);
            invalidate();
        }

        PointF[] getCorners() {
            PointF[] copy = new PointF[4];
            for (int i = 0; i < 4; i++) copy[i] = new PointF(corners[i].x, corners[i].y);
            return copy;
        }

        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (bitmap == null || getWidth() <= 0 || getHeight() <= 0) return;
            float scale = Math.min((float) getWidth() / bitmap.getWidth(), (float) getHeight() / bitmap.getHeight());
            float w = bitmap.getWidth() * scale;
            float h = bitmap.getHeight() * scale;
            float left = (getWidth() - w) / 2f;
            float top = (getHeight() - h) / 2f;
            imageRect.set(left, top, left + w, top + h);
            canvas.drawBitmap(bitmap, null, imageRect, null);

            Path path = new Path();
            PointF first = toView(corners[0]);
            path.moveTo(first.x, first.y);
            for (int i = 1; i < 4; i++) {
                PointF p = toView(corners[i]);
                path.lineTo(p.x, p.y);
            }
            path.close();
            canvas.drawPath(path, border);
            for (PointF corner : corners) {
                PointF p = toView(corner);
                canvas.drawCircle(p.x, p.y, dp(10), handle);
                canvas.drawCircle(p.x, p.y, dp(18), border);
            }
        }

        @Override public boolean onTouchEvent(MotionEvent event) {
            if (bitmap == null || imageRect.width() <= 0) return false;
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                activeCorner = nearestCorner(event.getX(), event.getY());
                return activeCorner >= 0;
            }
            if (event.getAction() == MotionEvent.ACTION_MOVE && activeCorner >= 0) {
                float bx = (event.getX() - imageRect.left) * bitmap.getWidth() / imageRect.width();
                float by = (event.getY() - imageRect.top) * bitmap.getHeight() / imageRect.height();
                bx = Math.max(0, Math.min(bitmap.getWidth() - 1, bx));
                by = Math.max(0, Math.min(bitmap.getHeight() - 1, by));
                corners[activeCorner].set(bx, by);
                invalidate();
                return true;
            }
            if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                activeCorner = -1;
                return true;
            }
            return true;
        }

        private int nearestCorner(float x, float y) {
            int best = -1;
            float bestDistance = dp(46);
            for (int i = 0; i < 4; i++) {
                PointF p = toView(corners[i]);
                float dx = x - p.x, dy = y - p.y;
                float d = (float) Math.sqrt(dx * dx + dy * dy);
                if (d < bestDistance) {
                    bestDistance = d;
                    best = i;
                }
            }
            return best;
        }

        private PointF toView(PointF bitmapPoint) {
            if (bitmap == null || imageRect.width() <= 0) return new PointF();
            float x = imageRect.left + bitmapPoint.x * imageRect.width() / bitmap.getWidth();
            float y = imageRect.top + bitmapPoint.y * imageRect.height() / bitmap.getHeight();
            return new PointF(x, y);
        }
    }
}
