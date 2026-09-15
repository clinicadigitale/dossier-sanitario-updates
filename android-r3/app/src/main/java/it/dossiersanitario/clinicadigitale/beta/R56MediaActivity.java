package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.StatFs;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;

public final class R56MediaActivity extends Activity {
    private static final String PREFS = "clinica_android_beta";
    private static final int PICK_DICOM_TREE = 5601;
    private static final int ACCENT = Color.rgb(15,118,110);
    private static final int ACCENT_DARK = Color.rgb(17,94,89);
    private static final int TEXT = Color.rgb(24,38,36);
    private static final int MUTED = Color.rgb(91,105,101);
    private static final int PAGE = Color.rgb(247,249,249);
    private static final int BORDER = Color.rgb(221,229,227);

    private SharedPreferences prefs;
    private LinearLayout content;
    private JSONObject pendingStudy;
    private ProgressBar progress;
    private TextView progressText;

    private static final class TreeItem {
        final Uri uri;
        final String relativePath;
        final long size;
        TreeItem(Uri u, String path, long s){uri=u;relativePath=path;size=Math.max(0L,s);}
    }

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs=getSharedPreferences(PREFS,MODE_PRIVATE);
        getWindow().setStatusBarColor(ACCENT_DARK);
        getWindow().setNavigationBarColor(Color.WHITE);
        setContentView(buildUi());
        render();
    }

    private View buildUi(){
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAGE);
        root.setFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((v,insets)->{
            v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });

        LinearLayout header=new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(16),dp(10),dp(16),dp(10));
        header.setBackgroundColor(Color.WHITE);
        Button back=ghostButton("‹");
        back.setTextSize(28);
        back.setOnClickListener(v->finish());
        header.addView(back,new LinearLayout.LayoutParams(dp(48),dp(46)));
        LinearLayout titles=new LinearLayout(this);titles.setOrientation(LinearLayout.VERTICAL);titles.setPadding(dp(10),0,0,0);
        titles.addView(text("Imaging e media",22,TEXT,true));
        titles.addView(text("DICOM e immagini associate",12,MUTED,false));
        header.addView(titles,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));
        root.addView(header);

        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(PAGE);
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(16),dp(16),dp(16),dp(32));
        scroll.addView(content,new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1f));
        return root;
    }

    private void render(){
        content.removeAllViews();
        JSONObject profile=R27ExactWindows.activeProfile(prefs);
        String profileName=R27ExactWindows.activeProfileName(prefs);

        LinearLayout intro=card();
        intro.addView(text(profileName,16,TEXT,true));
        intro.addView(text("Gli studi pesanti non vengono copiati automaticamente sul telefono. Puoi conservarne solo quelli che ti servono offline.",13,MUTED,false),top(6));
        long free=availableBytes();
        intro.addView(metricRow("Spazio libero sul dispositivo",R56StoragePolicy.formatBytes(free)),top(12));
        intro.addView(metricRow("Cache DICOM offline",R56StoragePolicy.formatBytes(offlineBytes())),top(4));
        content.addView(intro,bottom(14));

        JSONArray studies=R27ExactWindows.dicomStudies(prefs);
        LinearLayout dicom=card();
        dicom.addView(section("Studi DICOM"));
        if(studies.length()==0){
            dicom.addView(text("Nessuno studio DICOM presente nel catalogo sincronizzato.",13,MUTED,false));
        }else{
            for(int i=0;i<studies.length();i++){
                JSONObject study=studies.optJSONObject(i);if(study!=null)dicom.addView(studyView(study),top(i==0?4:12));
            }
        }
        content.addView(dicom,bottom(14));

        JSONArray images=R27ExactWindows.mediaAttachments(prefs);
        LinearLayout assoc=card();
        assoc.addView(section("Immagini associate ai referti"));
        if(images.length()==0)assoc.addView(text("Nessuna immagine associata nel catalogo sincronizzato.",13,MUTED,false));
        else{
            for(int i=0;i<images.length();i++){
                JSONObject image=images.optJSONObject(i);if(image==null)continue;
                String name=first(image,"name","originalName","title");if(name.isEmpty())name="Immagine associata";
                String detail=R56StoragePolicy.formatBytes(image.optLong("size",0L));
                TextView row=text(name+(detail.equals("0 B")?"":" · "+detail),13,TEXT,true);
                row.setPadding(0,dp(7),0,dp(7));assoc.addView(row);
            }
        }
        content.addView(assoc,bottom(14));

        LinearLayout info=card();
        info.setBackground(roundRect(Color.rgb(236,247,245),Color.rgb(190,222,217),18));
        info.addView(text("Spazio sotto controllo",15,ACCENT_DARK,true));
        info.addView(text("Prima di rendere uno studio disponibile offline, Clinica Digitale calcola dimensione richiesta, spazio disponibile e spazio residuo. Se lo spazio non basta, la copia non parte.",13,MUTED,false),top(6));
        content.addView(info,bottom(14));
    }

    private View studyView(JSONObject study){
        LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(dp(14),dp(13),dp(14),dp(13));
        box.setBackground(roundRect(Color.rgb(250,252,252),BORDER,16));
        String title=first(study,"studyDescription","description","title","modality");if(title.isEmpty())title="Studio DICOM";
        long bytes=study.optLong("totalBytes",0L);
        int count=study.optInt("fileCount",study.optJSONArray("files")==null?0:study.optJSONArray("files").length());
        File dir=offlineDir(study);
        boolean offline=dir.isDirectory()&&countDicom(dir)>0;
        box.addView(text(title,15,TEXT,true));
        String meta=(count>0?count+" file":"Studio")+(bytes>0?" · "+R56StoragePolicy.formatBytes(bytes):"");
        box.addView(text(meta,12,MUTED,false),top(3));
        TextView state=text(offline?"● Disponibile offline":"○ Solo catalogo",12,offline?ACCENT_DARK:MUTED,true);box.addView(state,top(7));
        String linked=linkedDocumentLabel(study.optString("linkedDocumentId",""));
        if(!linked.isEmpty())box.addView(text("Referto: "+linked,12,MUTED,false),top(4));

        if(offline){
            LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);actions.setPadding(0,dp(10),0,0);
            Button remove=ghostButton("Rimuovi dal telefono");remove.setOnClickListener(v->confirmRemove(study));actions.addView(remove,new LinearLayout.LayoutParams(0,dp(44),1f));
            box.addView(actions);
        }else{
            Button make=primaryButton("Rendi disponibile offline");make.setOnClickListener(v->prepareOffline(study));box.addView(make,top(10));
        }
        return box;
    }

    private void prepareOffline(JSONObject study){
        long required=study.optLong("totalBytes",0L);
        long available=availableBytes();
        R56StoragePolicy.Result result=R56StoragePolicy.evaluate(required,available);
        String msg="Spazio richiesto: "+R56StoragePolicy.formatBytes(required)+"\nSpazio disponibile: "+R56StoragePolicy.formatBytes(available)+"\nSpazio residuo previsto: "+R56StoragePolicy.formatBytes(result.remainingBytes);
        if(!result.enough){new AlertDialog.Builder(this).setTitle("Spazio insufficiente").setMessage(msg).setPositiveButton("Chiudi",null).show();return;}
        if(result.lowAfter)msg+="\n\nAttenzione: dopo la copia rimarrà poco spazio libero.";
        new AlertDialog.Builder(this).setTitle("Disponibile offline").setMessage(msg+"\n\nSeleziona la cartella originale dello studio, anche da memoria USB se collegata.")
                .setNegativeButton("Annulla",null).setPositiveButton("Seleziona cartella",(d,w)->pickTree(study)).show();
    }

    private void pickTree(JSONObject study){
        pendingStudy=study;
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION|Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        startActivityForResult(intent,PICK_DICOM_TREE);
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode!=PICK_DICOM_TREE)return;
        if(resultCode!=RESULT_OK||data==null||data.getData()==null||pendingStudy==null){pendingStudy=null;return;}
        Uri tree=data.getData();
        try{getContentResolver().takePersistableUriPermission(tree,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception ignored){}
        JSONObject study=pendingStudy;pendingStudy=null;
        scanAndCopy(study,tree);
    }

    private void scanAndCopy(JSONObject study,Uri tree){
        final AlertDialog dlg=progressDialog("Analisi cartella","Calcolo dei file DICOM e dello spazio necessario…");
        new Thread(()->{
            try{
                List<TreeItem> items=new ArrayList<>();
                collectTree(tree,"",items);
                long bytes=0L;int files=0;
                for(TreeItem x:items){if(isDicomName(x.relativePath)){bytes+=x.size;files++;}}
                if(files==0)throw new Exception("Nessun file DICOM trovato nella cartella selezionata");
                long free=availableBytes();R56StoragePolicy.Result result=R56StoragePolicy.evaluate(bytes,free);
                if(!result.enough)throw new Exception("Spazio insufficiente: servono "+R56StoragePolicy.formatBytes(bytes)+", disponibili "+R56StoragePolicy.formatBytes(free));
                final long required=bytes;final int total=files;
                runOnUiThread(()->{progressText.setText("Copia 0 / "+total+" · "+R56StoragePolicy.formatBytes(required));progress.setMax(total);progress.setProgress(0);});
                File target=offlineDir(study);deleteTree(target);if(!target.mkdirs()&&!target.isDirectory())throw new Exception("Impossibile creare l'archivio offline");
                int done=0;
                for(TreeItem x:items){
                    if(!isDicomName(x.relativePath))continue;
                    File out=new File(target,safeRelative(x.relativePath));File parent=out.getParentFile();if(parent!=null&&!parent.exists())parent.mkdirs();
                    copyUri(x.uri,out);done++;final int shown=done;
                    runOnUiThread(()->{progress.setProgress(shown);progressText.setText("Copia "+shown+" / "+total);});
                }
                long expected=study.optLong("totalBytes",0L);prefs.edit().putString("r56_offline_uri_"+safe(study.optString("id","study")),tree.toString()).apply();
                runOnUiThread(()->{dlg.dismiss();Toast.makeText(this,"Studio disponibile offline",Toast.LENGTH_LONG).show();render();});
            }catch(Exception e){runOnUiThread(()->{dlg.dismiss();new AlertDialog.Builder(this).setTitle("Copia non completata").setMessage(e.getMessage()).setPositiveButton("Chiudi",null).show();});}
        },"r56-media-copy").start();
    }

    private AlertDialog progressDialog(String title,String message){
        LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(dp(24),dp(10),dp(24),dp(10));
        progressText=text(message,13,MUTED,false);progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(100);box.addView(progressText);box.addView(progress,top(12));
        AlertDialog dlg=new AlertDialog.Builder(this).setTitle(title).setView(box).setCancelable(false).create();dlg.show();return dlg;
    }

    private void collectTree(Uri tree,String prefix,List<TreeItem> out)throws Exception{
        String docId=DocumentsContract.getTreeDocumentId(tree);
        Uri rootDoc=DocumentsContract.buildDocumentUriUsingTree(tree,docId);
        collectDocument(rootDoc,prefix,out);
    }

    private void collectDocument(Uri documentUri,String prefix,List<TreeItem> out)throws Exception{
        ContentResolver cr=getContentResolver();
        String docId=DocumentsContract.getDocumentId(documentUri);
        String name="";String mime="";long size=0L;
        try(Cursor c=cr.query(documentUri,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_SIZE},null,null,null)){
            if(c!=null&&c.moveToFirst()){name=c.getString(0);mime=c.getString(1);if(!c.isNull(2))size=c.getLong(2);}
        }
        String rel=prefix.isEmpty()?name:prefix+"/"+name;
        if(DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)){
            Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(documentUri,docId);
            try(Cursor c=cr.query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID},null,null,null)){
                if(c!=null)while(c.moveToNext()){
                    Uri child=DocumentsContract.buildDocumentUriUsingTree(documentUri,c.getString(0));collectDocument(child,rel,out);
                }
            }
        }else out.add(new TreeItem(documentUri,rel,size));
    }

    private void copyUri(Uri uri,File target)throws Exception{
        try(InputStream in=getContentResolver().openInputStream(uri);OutputStream out=new FileOutputStream(target)){
            if(in==null)throw new Exception("File sorgente non leggibile");byte[] buf=new byte[128*1024];int n;while((n=in.read(buf))>0)out.write(buf,0,n);
        }
    }

    private void confirmRemove(JSONObject study){
        new AlertDialog.Builder(this).setTitle("Rimuovere la copia offline?").setMessage("Il catalogo e il collegamento al referto restano nel Dossier. Vengono eliminati soltanto i file presenti su questo telefono.")
                .setNegativeButton("Annulla",null).setPositiveButton("Rimuovi",(d,w)->{deleteTree(offlineDir(study));render();}).show();
    }

    private String linkedDocumentLabel(String id){
        if(id==null||id.isEmpty())return "";JSONArray docs=R27ExactWindows.documents(prefs);
        for(int i=0;i<docs.length();i++){JSONObject d=docs.optJSONObject(i);if(d!=null&&id.equals(d.optString("id",""))){String s=first(d,"title","originalName","type");return s.isEmpty()?"Referto collegato":s;}}
        return "Referto collegato";
    }

    private File offlineDir(JSONObject study){return new File(new File(new File(getFilesDir(),"dicom_offline"),safe(R27ExactWindows.activeProfileId(prefs))),safe(study.optString("id","study")));}
    private long availableBytes(){return new StatFs(getFilesDir().getAbsolutePath()).getAvailableBytes();}
    private long offlineBytes(){return dirBytes(new File(getFilesDir(),"dicom_offline"));}
    private long dirBytes(File f){if(f==null||!f.exists())return 0L;if(f.isFile())return f.length();long n=0;File[] a=f.listFiles();if(a!=null)for(File x:a)n+=dirBytes(x);return n;}
    private int countDicom(File f){if(f==null||!f.exists())return 0;if(f.isFile())return isDicomName(f.getName())?1:0;int n=0;File[] a=f.listFiles();if(a!=null)for(File x:a)n+=countDicom(x);return n;}
    private void deleteTree(File f){if(f==null||!f.exists())return;if(f.isDirectory()){File[] a=f.listFiles();if(a!=null)for(File x:a)deleteTree(x);}f.delete();}
    private boolean isDicomName(String name){String n=name==null?"":name.toLowerCase();return n.endsWith(".dcm")||n.endsWith(".dicom")||(!n.contains(".")&&!n.endsWith("/"));}
    private String safe(String s){String x=s==null?"":s.replaceAll("[^A-Za-z0-9._-]+","_");return x.isEmpty()?"item":x;}
    private String safeRelative(String rel){String[] parts=(rel==null?"file.dcm":rel).replace('\\','/').split("/");StringBuilder b=new StringBuilder();for(String p:parts){if(p.isEmpty())continue;if(b.length()>0)b.append(File.separator);b.append(safe(p));}return b.length()==0?"file.dcm":b.toString();}
    private String first(JSONObject o,String...keys){if(o==null)return "";for(String k:keys){String v=o.optString(k,"").trim();if(!v.isEmpty())return v;}return "";}

    private LinearLayout card(){LinearLayout c=new LinearLayout(this);c.setOrientation(LinearLayout.VERTICAL);c.setPadding(dp(16),dp(16),dp(16),dp(16));c.setBackground(roundRect(Color.WHITE,BORDER,18));c.setElevation(dp(2));return c;}
    private TextView section(String s){TextView v=text(s,18,TEXT,true);v.setPadding(0,0,0,dp(8));return v;}
    private LinearLayout metricRow(String label,String value){LinearLayout r=new LinearLayout(this);r.setOrientation(LinearLayout.HORIZONTAL);r.addView(text(label,12,MUTED,false),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));TextView v=text(value,13,TEXT,true);v.setGravity(Gravity.END);r.addView(v);return r;}
    private Button primaryButton(String s){Button b=new Button(this);b.setAllCaps(false);b.setText(s);b.setTextSize(14);b.setTextColor(Color.WHITE);b.setBackground(roundRect(ACCENT,ACCENT_DARK,13));return b;}
    private Button ghostButton(String s){Button b=new Button(this);b.setAllCaps(false);b.setText(s);b.setTextSize(13);b.setTextColor(ACCENT_DARK);b.setBackground(roundRect(Color.WHITE,BORDER,13));return b;}
    private TextView text(String s,int sp,int color,boolean bold){TextView v=new TextView(this);v.setText(s);v.setTextSize(sp);v.setTextColor(color);if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);v.setLineSpacing(0,1.12f);return v;}
    private GradientDrawable roundRect(int fill,int stroke,int radius){GradientDrawable g=new GradientDrawable();g.setColor(fill);g.setCornerRadius(dp(radius));g.setStroke(dp(1),stroke);return g;}
    private LinearLayout.LayoutParams top(int d){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,dp(d),0,0);return p;}
    private LinearLayout.LayoutParams bottom(int d){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,0,0,dp(d));return p;}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
}
