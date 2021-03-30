const items = (obj) => {
    var i, arr = [];
    for(i in obj) {
        arr.push(obj[i]);
    }
    return arr;
};
const commaFormat = (x) => {
    try {return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");}
    catch {return x;}
};
exports.commaFormat = commaFormat;
exports.items = items;