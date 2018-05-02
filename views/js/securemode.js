function switchsafemode(matchClass) {
    rules_id = {"email" : 0, "hash":1, "plain": 2};
    //alert(document.getElementById("chk_"+matchClass).checked);
    if (document.getElementById("chk_"+matchClass).checked == false){
        //si déjà visible / coché : il faut flouter
        document.styleSheets[0].insertRule("."+matchClass+" {filter: blur(3px);}", rules_id[matchClass]);
        document.getElementById("chk_"+matchClass).checked = false;
    }
    else{
        document.styleSheets[0].deleteRule(rules_id[matchClass])
        document.getElementById("chk_"+matchClass).checked = true;
    }/*

            var elems = document.getElementsByTagName('span'), i;
            for (i in elems) {
                if((' ' + elems[i].className + ' ').indexOf(' ' + matchClass + ' ')> -1) {
                    if (elems[i].style.filter == "blur(3px)"){
                        document.getElementById("chk_"+matchClass).checked = true;
                        elems[i].style.filter = "blur(0px)";
                    }
                    else{
                        elems[i].style.filter = "blur(3px)";
                        document.getElementById("chk_"+matchClass).checked = false;
                    }
                }
            }*/
        }